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

def find_existing_targets(locus, cone_search_radius_arcsec:float=2) -> QuerySet:
    """
    Look for an existing target at the same coordinates as the input target
    """

    try:
        cone_search_radius = settings.CONE_SEARCH_RADIUS/3600
    except AttributeError:
        cone_search_radius = cone_search_radius_arcsec/3600
        logger.warning(f"Setting the cone search radius to {cone_search_radius_arcsec} arcsec! Set settings.CONE_SEARCH_RADIUS if you would like to use a different value.")
        
    return cone_search_filter(
        queryset = Target.objects.all(),
        ra = locus.ra,
        dec = locus.dec,
        radius = cone_search_radius
    )


def handle_alert(locus):
    """
    Ingests the locus into a new target object (or updates an existing one)
    """
    target_matches = find_existing_targets(locus)
    logger.info(f"Target matches: {target_matches}")
    
    broker = ANTARESBroker()
    alert = broker.alert_to_dict(locus)

    if target_matches.count():
        # then this target already exists in the Targets table
        target = target_matches.order_by("separation").first()

        logger.info(f"Found existing target matching this alert: {target.name}")
        created = False
        
        # update the TargetName objects returned to instead point to the existing target
        aliases = broker.aliases_from_locus(alert, target)
        
    else:
        # then this target does not exist, so we create it from scratch
        logger.info(f"No existing target found, adding as new target")
        target, _, aliases = broker.to_target(alert)
        created = True
        
    broker.process_reduced_data(target, alert)

    # save the aliases that we found for this target
    logger.info(f"Adding {aliases} to {target}")
    aliases_added = []
    for alias in aliases:
        existing_alias = TargetName.objects.filter(name=alias.name)
        if not existing_alias.exists():
            alias.save()
            aliases_added.append(alias.name)
        elif TargetName.objects.filter(
            name=alias.name
        ).exclude(
            target=target
        ).exists():
            # this will happen if the alias exists under a different target
            # than the one we are trying to save it with
            # in which case we should log a warning
            logger.warning(
                f"The name alias {alias.name} exists under the target " +
                f" {existing_alias.first().target}, which is different from the nearest " + 
                f"target in the existing database (which is {target}). We are "+
                "NOT re-assigning this alias!"
            )
    
    return target, created, aliases_added
