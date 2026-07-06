from django.core.management.base import BaseCommand

from apps.inventory.services import rebuild_stock_balances


class Command(BaseCommand):
    help = (
        "Recompute all stock balances from the full ledger and report drift "
        "(TECHNICAL_ARCHITECTURE §5.3 consistency check)."
    )

    def handle(self, *args, **options):
        drift = rebuild_stock_balances()
        if drift:
            for line in drift:
                self.stdout.write(self.style.WARNING(f"drift: {line}"))
            self.stdout.write(self.style.WARNING(f"{len(drift)} balance(s) corrected."))
        else:
            self.stdout.write(self.style.SUCCESS("Balances reconcile with the ledger."))
