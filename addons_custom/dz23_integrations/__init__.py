# -*- coding: utf-8 -*-
import base64
import logging
import os

from . import models

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Carrega os logos (static/logos/<key>.png) em cada integração dz23."""
    base = os.path.join(os.path.dirname(__file__), "static", "logos")
    if not os.path.isdir(base):
        return
    for fn in os.listdir(base):
        if not fn.endswith(".png"):
            continue
        key = fn[:-4]
        rec = env.ref("dz23_integrations.int_%s" % key, raise_if_not_found=False)
        if not rec:
            continue
        try:
            with open(os.path.join(base, fn), "rb") as fh:
                rec.logo = base64.b64encode(fh.read())
        except Exception as e:  # noqa: BLE001
            _logger.warning("DZ23 integrations: falha ao carregar logo %s: %s", fn, e)
