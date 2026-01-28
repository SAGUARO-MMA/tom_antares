from django.core.management.base import BaseCommand
from antares_client import StreamingClient
from django.conf import settings
from ...handlers import run_handler
import logging

logger = logging.getLogger(__name__)

broker_config = settings.BROKERS['ANTARES'].copy()
topics = broker_config.pop('topics', [])


class Command(BaseCommand):
    help = "Listen for alerts from the ANTARES broker."

    def handle(self, *args, **options):
        with StreamingClient(topics, **broker_config) as client:
            for topic, locus in client.iter():
                logger.info(f"received {locus.locus_id} on {topic}")
                run_handler(topic, locus)
