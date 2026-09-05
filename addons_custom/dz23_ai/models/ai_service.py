# Serviço de IA plugável. Provedores:
#   - ollama  : LOCAL e GRÁTIS (sem custo de token) — http://host:11434
#   - groq    : free-tier (OpenAI-compatible)
#   - google  : Gemini free-tier
#   - openai  : pago
#   - anthropic: pago
# Chaves/base ficam em ir.config_parameter (Ajustes), nunca no código.
import logging
import re

import requests
from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)
_TIMEOUT = 120  # modelos locais podem ser lentos

_OPENAI_COMPAT_BASE = {
    "groq": "https://api.groq.com/openai/v1",
    "openai": "https://api.openai.com/v1",
}
_LOCAL_PROVIDERS = ("ollama",)

# Redação de PII para o que sai a provedores EXTERNOS.
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_RE_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_RE_DOC = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")


def _safe_url(url):
    """URL sem query string (evita vazar chave/token em log)."""
    return (url or "").split("?", 1)[0]


def _redact_pii(text):
    """Mascara e-mail, telefone e CPF/CNPJ antes de enviar a IA externa."""
    if not text:
        return text
    text = _RE_EMAIL.sub("[email]", text)
    text = _RE_DOC.sub("[documento]", text)
    text = _RE_PHONE.sub("[telefone]", text)
    return text


class DZ23AI(models.AbstractModel):
    _name = "dz23.ai"
    _description = "DZ23 — Serviço de IA (local grátis + free-tier + pago)"

    def _cfg(self, key, default=""):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _provider(self):
        return (self._cfg("dz23.ai_provider", "ollama") or "ollama").strip()

    def _model(self):
        return self._cfg("dz23.ai_model", "") or self._default_model()

    def _default_model(self):
        return {
            "ollama": "llama3.2:3b",
            "groq": "llama-3.3-70b-versatile",
            "google": "gemini-1.5-flash",
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-5-sonnet-latest",
        }.get(self._provider(), "llama3.2:3b")

    def _external_allowed(self):
        """Política: provedores externos só com consentimento explícito."""
        val = self._cfg("dz23.ai.external_allowed", "0")
        return (val or "0") not in ("0", "False", "false", "")

    def _post(self, url, **kwargs):
        try:
            resp = requests.post(url, timeout=_TIMEOUT, **kwargs)
        except requests.exceptions.RequestException:
            # NUNCA logar a exceção crua (pode conter URL com query/segredo).
            _logger.warning("DZ23 IA erro de rede (%s) em %s", self._provider(), _safe_url(url))
            raise UserError(_("Não foi possível contatar a IA (%s).") % self._provider()) from None
        if resp.status_code >= 400:
            _logger.info("DZ23 IA %s -> %s", _safe_url(url), resp.status_code)
            raise UserError(_("A IA recusou a requisição (código %s).") % resp.status_code)
        return resp.json()

    # ---------- API pública ----------
    @api.model
    def chat(self, prompt, system=None, image_b64=None):
        """Envia um prompt e retorna o texto. Local (Ollama) por padrão;
        provedores externos exigem política explícita e recebem PII redigida."""
        if not prompt:
            raise UserError(_("Prompt vazio."))
        provider = self._provider()
        fn = {
            "ollama": self._ollama,
            "groq": self._openai_compat,
            "openai": self._openai_compat,
            "google": self._gemini,
            "anthropic": self._anthropic,
        }.get(provider)
        if not fn:
            raise UserError(_("Provedor de IA não suportado: %s") % provider)
        # GATE de privacidade: externo só com política; e redige PII antes de sair.
        if provider not in _LOCAL_PROVIDERS:
            if not self._external_allowed():
                raise UserError(
                    _(
                        "Provedor de IA externo (%s) está desativado por política. "
                        "Use o modelo local (Ollama) ou ative dz23.ai.external_allowed "
                        "com consentimento/base legal registrados."
                    )
                    % provider
                )
            prompt = _redact_pii(prompt)
            system = _redact_pii(system)
        return fn(prompt, system, image_b64)

    # ---------- Adaptadores ----------
    def _ollama(self, prompt, system, image_b64):
        base = (self._cfg("dz23.ai.ollama_base", "http://host.docker.internal:11434")).rstrip("/")
        msg = {"role": "user", "content": prompt}
        if image_b64:
            msg["images"] = [image_b64]
        messages = ([{"role": "system", "content": system}] if system else []) + [msg]
        data = self._post(
            "%s/api/chat" % base,
            json={
                "model": self._model(),
                "messages": messages,
                "stream": False,
                # Respostas naturais porém curtas e estáveis (tom de WhatsApp).
                "options": {
                    "temperature": 0.6,
                    "top_p": 0.9,
                    "repeat_penalty": 1.2,
                    "num_predict": 220,
                },
            },
        )
        return (data.get("message") or {}).get("content", "")

    def _openai_compat(self, prompt, system, image_b64):
        provider = self._provider()
        key = self._cfg("dz23.ai.%s_key" % provider)
        if not key:
            raise UserError(_("Configure a chave de API do %s em Ajustes.") % provider)
        base = self._cfg("dz23.ai.%s_base" % provider) or _OPENAI_COMPAT_BASE.get(provider)
        if image_b64:
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,%s" % image_b64}},
            ]
        else:
            content = prompt
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": content}
        ]
        data = self._post(
            "%s/chat/completions" % base.rstrip("/"),
            headers={"Authorization": "Bearer %s" % key},
            json={"model": self._model(), "messages": messages},
        )
        return data["choices"][0]["message"]["content"]

    def _anthropic(self, prompt, system, image_b64):
        key = self._cfg("dz23.ai.anthropic_key")
        if not key:
            raise UserError(_("Configure a chave de API da Anthropic em Ajustes."))
        content = [{"type": "text", "text": prompt}]
        if image_b64:
            content.append(
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": image_b64},
                }
            )
        payload = {
            "model": self._model(),
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": content}],
        }
        if system:
            payload["system"] = system
        data = self._post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json=payload,
        )
        return data["content"][0]["text"]

    def _gemini(self, prompt, system, image_b64):
        key = self._cfg("dz23.ai.google_key")
        if not key:
            raise UserError(_("Configure a chave de API do Google (Gemini) em Ajustes."))
        parts = [{"text": prompt}]
        if image_b64:
            parts.append({"inline_data": {"mime_type": "image/png", "data": image_b64}})
        payload = {"contents": [{"parts": parts}]}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        # Chave no HEADER (x-goog-api-key), NUNCA na query string (evita log leak).
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent"
            % self._model()
        )
        data = self._post(url, headers={"x-goog-api-key": key}, json=payload)
        return data["candidates"][0]["content"]["parts"][0]["text"]
