"""
Functions to deal with targets after they are created from the Antares Stream
"""
import logging
from typing import Union
from django.conf import settings
from django.db.models.query import QuerySet

from tom_targets.models import Target, TargetName
from tom_targets.utils import cone_search_filter

from .antares import ANTARESBroker

logger = logging.getLogger(__name__)

def find_existing_targets(target:Target, cone_search_radius_arcsec:float=2) -> QuerySet:
    """
    Look for an existing target at the same coordinates as the input target
    """

    try:
        cone_search_radius = settings.CONE_SEARCH_RADIUS
    except AttributeError:
        cone_search_radius = cone_search_radius_arcsec/3600
        logger.warning(f"Setting the cone search radius to {cone_search_radius_arcsec} arcsec! Set settings.CONE_SEARCH_RADIUS if you would like to use a different value.")
        
    return cone_search_filter(
        queryset = Target.objects.all(),
        ra = target.ra,
        dec = target.dec,
        radius = cone_search_radius
    )

def run_handler(topic, locus):
    """
    Ingests the locus into a new target object (or updates an existing one)
    """

    broker = ANTARESBroker()
    target, _, aliases = broker.to_target(locus.__dict__)

    target_matches = find_existing_targets(target)
    if target_matches.count():
        # then this target already exists in the Targets table
        existing_target = target_matches.first()

        # update the TargetName objects returned to instead point to the existing target
        for alias in aliases:
            alias.target = existing_target
            alias.save()
    else:
        # then this target does not exist, so we create it from scratch
        target.save()
