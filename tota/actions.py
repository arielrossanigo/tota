import random

from tota.utils import distance
from tota import settings


def check_cooldown(last_uses_key, cooldown):
    def decorator(f):
        def action_with_cooldown_check(thing, world, target_position):
            if last_uses_key in thing.last_uses:
                ready = world.t - thing.last_uses[last_uses_key] > cooldown
            else:
                ready = True

            if not ready:
                event = "tried to heal but it's on cooldown"
            else:
                event = f(thing, world, target_position)

            return event

        return action_with_cooldown_check

    return decorator


def check_distance(action_distance):
    def decorator(f):
        def action_with_distance_check(thing, world, target_position):
            if distance(thing, target_position) > action_distance:
                event = 'too far away'
            else:
                event = f(thing, world, target_position)

            return event

        return action_with_distance_check

    return decorator


def check_target_position(f):
    def action_with_target_check(thing, world, target_position):
        if not isinstance(target_position, tuple):
            event = "tried to perform an action into a target that isn't a position"
        else:
            event = f(thing, world, target_position)

        return event

    return action_with_target_check


def update_last_use(thing, world, last_uses_key):
    thing.last_uses[last_uses_key] = world.t


def calculate_damage(thing, base_damage, level_multiplier=None):
    damage = random.randint(*base_damage)

    if level_multiplier is not None:
        if hasattr(thing, 'level'):
            level = thing.level
        else:
            level = 0

        damage_multiplier = 1 + (level * level_multiplier)
    else:
        damage_multiplier = 1

    return damage * damage_multiplier


@check_target_position
@check_distance(settings.MOVE_DISTANCE)
def move(thing, world, target_position):
    obstacle = world.things.get(target_position)
    if obstacle is not None:
        event = 'hit {} with his head'.format(obstacle.name)
    else:
        # we store position in the things, because they need to know it,
        # but also in our dict, for faster access
        world.things[target_position] = thing
        del world.things[thing.position]
        thing.position = target_position

        event = 'moved to {}'.format(target_position)

    return event


@check_target_position
@check_distance(settings.HERO_ATTACK_DISTANCE)
def hero_attack(thing, world, target_position):
    target = world.things.get(target_position)
    if target is None:
        event = 'nothing there to attack'
    else:
        damage = calculate_damage(thing,
                                  settings.HERO_ATTACK_BASE_DAMAGE,
                                  settings.HERO_ATTACK_LEVEL_MULTIPLIER)

        target.life -= damage
        event = 'damaged {} by {}'.format(target.name, damage)

    return event


@check_target_position
@check_distance(settings.TOWER_ATTACK_DISTANCE)
def tower_attack(thing, world, target_position):
    target = world.things.get(target_position)
    if target is None:
        event = 'nothing there to attack'
    else:
        damage = calculate_damage(thing,
                                  settings.TOWER_ATTACK_BASE_DAMAGE)

        target.life -= damage
        event = 'damaged {} by {}'.format(target.name, damage)

    return event


@check_target_position
@check_distance(settings.CREEP_ATTACK_DISTANCE)
def creep_attack(thing, world, target_position):
    target = world.things.get(target_position)
    if target is None:
        event = 'nothing there to attack'
    else:
        damage = calculate_damage(thing,
                                  settings.CREEP_ATTACK_BASE_DAMAGE)

        target.life -= damage
        event = 'damaged {} by {}'.format(target.name, damage)

    return event


@check_target_position
@check_distance(settings.HEAL_DISTANCE)
@check_cooldown('heal', settings.HEAL_COOLDOWN)
def heal(thing, world, target_position):
    event_bits = []
    for position, target in world.things.items():
        if distance(target_position, target) <= settings.HEAL_RADIUS:
            # heal avoiding health overflow
            heal = calculate_damage(thing,
                                    settings.HEAL_BASE_HEALING,
                                    settings.HEAL_LEVEL_MULTIPLIER)

            target.life = min(target.max_life, target.life + heal)

            event_bits.append('healed {} by {}'.format(target.name, heal))

    return ', '.join(event_bits)


@check_target_position
@check_distance(settings.FIREBALL_DISTANCE)
@check_cooldown('fireball', settings.FIREBALL_COOLDOWN)
def fireball(thing, world, target_position):
    event_bits = []
    for position, target in world.things.items():
        if distance(target_position, target) <= settings.FIREBALL_RADIUS:
            damage = calculate_damage(thing,
                                      settings.FIREBALL_BASE_DAMAGE,
                                      settings.FIREBALL_LEVEL_MULTIPLIER)

            target.life -= damage

            event_bits.append('damaged {} with fire by {}'.format(target.name,
                                                                  damage))

    return ', '.join(event_bits)


@check_target_position
@check_distance(settings.STUN_DISTANCE)
@check_cooldown('fireball', settings.STUN_COOLDOWN)
def stun(thing, world, target_position):
    target = world.things.get(target_position)
    if target is None:
        event = 'nothing there to stun'
    else:
        target.disabled_until = world.t + settings.STUN_DURATION
        event = 'stuned {}'.format(target.name)

    return event
