/*
 * Ascension native-game localization bridge.
 *
 * The original ROM remains the source of truth. When PT-BR is active,
 * selected English strings are replaced immediately before rendering.
 * Anything not translated falls back to the original ROM text.
 */

#include <string.h>

#include "ascension_locale.h"

struct AscensionGameString {
    const char *en;
    const char *pt_br;
};

static const struct AscensionGameString kPtBrGame[] = {
    /* Front-end navigation */
    { "START\n",              "INICIAR\n" },
    { "NEXT\n",               "PROXIMO\n" },
    { "PREVIOUS\n",           "ANTERIOR\n" },

    /* Difficulty */
    { "Agent",                "Agente" },
    { "Secret Agent",         "Agente Secreto" },
    { "00 Agent",             "Agente 00" },
    { "Agent\n",              "Agente\n" },
    { "Secret Agent\n",       "Agente Secreto\n" },
    { "00 Agent\n",           "Agente 00\n" },

    /* File select */
    { "Erase file?\n",        "Apagar arquivo?\n" },
    { "cancel\n",             "cancelar\n" },
    { "confirm\n",            "confirmar\n" },
    { "Mission ",             "Missao " },
    { "Copy\n",               "Copiar\n" },
    { "Erase\n",              "Apagar\n" },

    /* Mode select */
    { "SELECT MISSION\n",     "SELECIONAR MISSAO\n" },
    { "MULTIPLAYER\n",        "MULTIJOGADOR\n" },
    { "CHEAT OPTIONS\n",      "OPCOES DE TRAPACA\n" },

    /* Common status */
    { "Completed\n",          "Concluido\n" },
    { "FAILED\n",             "FALHOU\n" },
    { "PRIMARY OBJECTIVES:\n", "OBJETIVOS PRINCIPAIS:\n" },
    { "BACKGROUND:\n",        "CONTEXTO:\n" },
    { "M BRIEFING:\n",        "INSTRUCOES DE M:\n" },
    { "Q BRANCH:\n",          "DIVISAO Q:\n" },
    { "MONEYPENNY:\n",        "MONEYPENNY:\n" },
    { "REPORT:\n",            "RELATORIO:\n" },
    { "Mission status:\n",    "Status da missao:\n" },
    { " ABORTED\n",           " ABORTADA\n" },
    { " Completed\n",         " Concluida\n" },
    { " FAILED\n",            " FALHOU\n" },

    /* Statistics */
    { "STATISTICS:\n",        "ESTATISTICAS:\n" },
    { "Time:\n",              "Tempo:\n" },
    { "Accuracy:\n",          "Precisao:\n" },
    { "Weapon of choice:\n",  "Arma preferida:\n" },
    { "Shot total:\n",        "Total de disparos:\n" },
    { "Head hits:\n",         "Acertos na cabeca:\n" },
    { "Body hits:\n",         "Acertos no corpo:\n" },
    { "Limb hits:\n",         "Acertos nos membros:\n" },
    { "Others:\n",            "Outros:\n" },
    { "Kill total:\n",        "Total de eliminacoes:\n" },

    /* Generic options */
    { "ON\n",                 "LIGADO\n" },
    { "OFF\n",                "DESLIGADO\n" },
};

#define NUM_PTBR_GAME \
    ((int)(sizeof(kPtBrGame) / sizeof(kPtBrGame[0])))

const char *ascensionLocaleGameText(int slotID, const char *fallback)
{
    int i;

    (void)slotID;

    if (fallback == NULL || ascensionLocaleGet() != 1)
        return fallback;

    for (i = 0; i < NUM_PTBR_GAME; i++) {
        if (strcmp(fallback, kPtBrGame[i].en) == 0)
            return kPtBrGame[i].pt_br;
    }

    return fallback;
}
