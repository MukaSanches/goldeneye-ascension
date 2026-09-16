#include "platform.h"
#include "config.h"
#include "ascension_campaign.h"

/*
 * Defaults OFF. The setting is persisted in the normal PC config, never in a
 * GoldenEye save slot. Turning it off immediately restores native progression
 * checks because no mission-completion bits are fabricated by this policy.
 */
static int s_unlockAllMissions = 0;

PD_CONSTRUCTOR static void ascensionCampaignConfigInit(void)
{
    configRegisterInt("Ascension.UnlockAllMissions", &s_unlockAllMissions, 0, 1);
}

int ascensionCampaignUnlockAllMissions(void)
{
    return s_unlockAllMissions != 0;
}
