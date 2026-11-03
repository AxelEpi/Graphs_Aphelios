"""
helper.py : état et règles d'Aphelios (armes, munitions, cooldowns).
Source : https://wiki.leagueoflegends.com/en-us/Aphelios
"""

# =============================================================================
# 1. CONSTANTES
# =============================================================================

# Numéro de l'arme -> infos (ordre initial du cycle : 1, 2, 3, 4, 5)
WEAPON_NAMES = {
    1: "Calibrum",
    2: "Severum",
    3: "Gravitum",
    4: "Infernum",
    5: "Crescendum",
}
WEAPON_COLORS = {
    1: "red",
    2: "green",
    3: "blue",
    4: "purple",
    5: "white",
}
# Capacité primaire (Q) associée à chaque arme quand elle est en main principale
PRIMARY_ABILITIES = {
    1: "Moonshot",
    2: "Onslaught",
    3: "Binding Eclipse",
    4: "Duskwave",
    5: "Sentry",
}

# --- Munitions (Moonlight) ---
MAX_MOONLIGHT = 50        # 30 sur la map Arena
ABILITY_COST = 10         # coût en munitions d'une capacité primaire
ATTACK_COST = 1           # coût d'une attaque de base

# --- Temps (en secondes) ---
PHASE_COOLDOWN = 0.8              # cooldown statique de Phase (W)
ASSEMBLY_TIME = 1.0               # durée d'assemblage de la nouvelle arme
ASSEMBLY_ABILITY_COOLDOWN = 1.5   # cooldown imposé à la capacité primaire de la nouvelle arme

# Cooldown des capacités primaires : (niveau 1, niveau 18). Le wiki donne seulement
# "10 - 8 (selon le niveau)", donc on interpole linéairement entre les deux.
MAX_LEVEL = 18
ABILITY_COOLDOWNS = {
    1: (10, 8),   # Moonshot
    2: (10, 8),   # Onslaught
    3: (12, 10),  # Binding Eclipse
    4: (9, 6),    # Duskwave
    5: (9, 6),    # Sentry
}
# Ultime (Moonlight Vigil) : cooldown selon le niveau où il est débloqué/amélioré
ULTIMATE_COOLDOWNS = {6: 120, 11: 110, 16: 100}


# =============================================================================
# 2. ÉTAT DU JEU
# =============================================================================

cycle = [1, 2, 3, 4, 5]                       # [main, off-hand, réserve 1, 2, 3]
ammo = {w: MAX_MOONLIGHT for w in WEAPON_NAMES}  # munitions PAR arme
level = 1
now = 0.0                                     # horloge de la partie (secondes)

# Moment (en secondes) à partir duquel chaque chose est de nouveau disponible
ability_ready_at = {w: 0.0 for w in WEAPON_NAMES}  # cooldowns non partagés entre armes
phase_ready_at = 0.0
ultimate_ready_at = 0.0
assembly_ends_at = 0.0


# =============================================================================
# 3. GETTERS
# =============================================================================

def get_weapon_color(weapon_number):
    """Couleur d'une arme à partir de son numéro."""
    return WEAPON_COLORS.get(weapon_number, "Unknown weapon number")


def get_weapon_cycle():
    """Cycle actuel : [main, off-hand, réserve...]."""
    return cycle


def get_cycle_colors():
    """Couleurs des armes dans l'ordre du cycle."""
    return [get_weapon_color(w) for w in cycle]


def get_weapon_binome():
    """Binôme = (main, off-hand). Calculé à la volée pour ne jamais être périmé."""
    return cycle[0], cycle[1]


def get_binome_colors():
    return tuple(get_weapon_color(w) for w in get_weapon_binome())


# =============================================================================
# 4. TEMPS ET COOLDOWNS
# =============================================================================

def advance_time(seconds):
    """Fait avancer l'horloge de la partie."""
    global now
    now += seconds
    return now


def get_ability_cooldown(weapon_number):
    """Cooldown (s) de la capacité primaire d'une arme au niveau actuel."""
    cd_start, cd_end = ABILITY_COOLDOWNS[weapon_number]
    progress = (level - 1) / (MAX_LEVEL - 1)
    return cd_start + (cd_end - cd_start) * progress


def get_ultimate_cooldown():
    """Cooldown (s) de Moonlight Vigil au niveau actuel (None avant le niveau 6)."""
    unlocked = [lvl for lvl in ULTIMATE_COOLDOWNS if lvl <= level]
    if not unlocked:
        return None
    return ULTIMATE_COOLDOWNS[max(unlocked)]


def is_assembling():
    return now < assembly_ends_at


def is_ability_ready(weapon_number):
    return now >= ability_ready_at[weapon_number]


def is_phase_ready():
    # Phase est bloquée pendant l'assemblage d'une nouvelle arme
    return now >= phase_ready_at and not is_assembling()


def get_remaining_cooldown(weapon_number):
    return max(0.0, ability_ready_at[weapon_number] - now)


# =============================================================================
# 5. ACTIONS
# =============================================================================

def phase_skill():
    """Phase (W) : échange main et off-hand. Cooldown fixe de 0.8 s."""
    global phase_ready_at
    if not is_phase_ready():
        print("Phase indisponible (cooldown ou assemblage en cours).")
        return cycle
    cycle[0], cycle[1] = cycle[1], cycle[0]
    phase_ready_at = now + PHASE_COOLDOWN
    print(f"After phase skill: {cycle}")
    return cycle


def weapon_exhausted():
    """
    L'arme principale est vidée : elle va en fin de réserve (et sera rechargée),
    la 1re arme de la réserve devient la main principale. L'off-hand ne bouge pas.
    Avant : [main, off, r1, r2, r3]  ->  Après : [r1, off, r2, r3, main]
    """
    global cycle, assembly_ends_at
    old_main = cycle[0]
    cycle = [cycle[2], cycle[1]] + cycle[3:] + [old_main]
    ammo[old_main] = MAX_MOONLIGHT          # elle sera "refabriquée" par Alune

    new_main = cycle[0]
    assembly_ends_at = now + ASSEMBLY_TIME
    # La capacité primaire de la nouvelle arme est bloquée 1.5 s dès le début de l'assemblage
    ability_ready_at[new_main] = max(ability_ready_at[new_main],
                                     now + ASSEMBLY_ABILITY_COOLDOWN)
    print(f"Weapon exhausted ! New cycle: {cycle}")
    return cycle


def use_munition():
    """Attaque de base : consomme 1 munition de l'arme principale."""
    main = cycle[0]
    if is_assembling():
        print("Assemblage en cours, impossible d'attaquer.")
        return ammo[main]
    ammo[main] -= ATTACK_COST
    print(f"Used one munition. Remaining: {ammo[main]}")
    if ammo[main] <= 0:
        weapon_exhausted()
    return ammo[cycle[0]]


def primary_ability():
    """
    Capacité primaire de l'arme principale : 10 munitions + cooldown propre à l'arme.
    Sous 10 munitions, la capacité reste lançable et consomme tout ce qu'il reste.
    """
    main = cycle[0]
    if is_assembling() or not is_ability_ready(main):
        print(f"{PRIMARY_ABILITIES[main]} en cooldown "
              f"({get_remaining_cooldown(main):.1f}s restantes).")
        return False

    ammo[main] -= min(ABILITY_COST, ammo[main])
    ability_ready_at[main] = now + get_ability_cooldown(main)
    print(f"{PRIMARY_ABILITIES[main]} activated! Munitions restantes : {ammo[main]}")
    if ammo[main] <= 0:
        weapon_exhausted()
    return True


def ultimate():
    """Moonlight Vigil (R) : niveau 6 minimum, cooldown 120/110/100 s."""
    global ultimate_ready_at
    cooldown = get_ultimate_cooldown()
    if cooldown is None:
        print("Ultime non débloqué (niveau 6 requis).")
        return False
    if now < ultimate_ready_at:
        print(f"Moonlight Vigil en cooldown ({ultimate_ready_at - now:.1f}s restantes).")
        return False
    ultimate_ready_at = now + cooldown
    print("Moonlight Vigil activated!")
    return True


def set_binome_goal(main_weapon_number, off_hand_weapon_number):
    """Objectif de binôme à atteindre (ne modifie pas le cycle actuel)."""
    return main_weapon_number, off_hand_weapon_number


# =============================================================================
# 6. DÉMO
# =============================================================================

if __name__ == "__main__":
    print(get_cycle_colors(), get_binome_colors())
    primary_ability()          # Moonshot : lancée
    primary_ability()          # refusée : cooldown
    advance_time(10)
    primary_ability()          # de nouveau dispo
    phase_skill()              # swap
    phase_skill()              # refusée : 0.8 s pas écoulées