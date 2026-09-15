#ifndef ASCENSION_CAMPAIGN_H
#define ASCENSION_CAMPAIGN_H

/*
 * Port-owned campaign access policy.
 *
 * This is intentionally an access override, not a save-game editor. Enabling
 * it makes normally eligible missions selectable while leaving completion
 * flags, best times, cheats and EEPROM data untouched by the toggle itself.
 */
int ascensionCampaignUnlockAllMissions(void);

#endif /* ASCENSION_CAMPAIGN_H */
