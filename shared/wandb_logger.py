"""Optional Weights & Biases logging wrapper for experiment tracking.

Provides a thin, graceful-degradation wrapper around the ``wandb`` Python SDK.
All public methods are safe to call even when ``wandb`` is not installed or
no API key is configured -- they will simply log a debug message and return.
"""

import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class WandbLogger:
    """Optional experiment tracker backed by Weights & Biases.

    Usage::

        logger = WandbLogger(project="observatory")
        logger.log({"metric": 0.95})
        logger.close()
    """

    def __init__(
        self,
        project: str = "sovereign-intelligence-observatory",
        config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
    ):
        self._run = None
        self._enabled = False
        self._init(project, config, api_key)

    def _init(
        self,
        project: str,
        config: Optional[Dict[str, Any]],
        api_key: Optional[str],
    ) -> None:
        api_key = api_key or os.getenv("WANDB_API_KEY")
        if not api_key:
            logger.debug("wandb: no API key found; tracking disabled")
            return
        try:
            import wandb

            self._run = wandb.init(
                project=project,
                config=config,
                mode="online" if api_key else "offline",
                anonymous="never",
            )
            self._enabled = True
            logger.info("wandb: tracking enabled for project '%s'", project)
        except ImportError:
            logger.debug("wandb: package not installed; tracking disabled")
        except Exception as exc:
            logger.debug("wandb: init failed: %s", exc)

    def log(self, data: Dict[str, Any], step: Optional[int] = None) -> None:
        if not self._enabled or self._run is None:
            return
        try:
            self._run.log(data, step=step)
        except Exception as exc:
            logger.debug("wandb: log failed: %s", exc)

    def log_summary(self, summary: Dict[str, Any]) -> None:
        if not self._enabled or self._run is None:
            return
        try:
            for k, v in summary.items():
                self._run.summary[k] = v
        except Exception as exc:
            logger.debug("wandb: summary failed: %s", exc)

    def watch_model(self, model: Any) -> None:
        if not self._enabled or self._run is None:
            return
        try:
            import wandb

            wandb.watch(model)
        except Exception as exc:
            logger.debug("wandb: watch failed: %s", exc)

    def close(self) -> None:
        if self._run is not None:
            try:
                self._run.finish()
            except Exception as exc:
                logger.debug("wandb: finish failed: %s", exc)
            self._run = None
            self._enabled = False
