from celery import shared_task

from .services import rebuild_stock_balances


@shared_task
def rebuild_stock_balances_task():
    """Scheduled/on-demand drift check (TECHNICAL_ARCHITECTURE §5.3)."""
    return rebuild_stock_balances()
