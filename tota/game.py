import os
import time

from termcolor import colored

from tota.world import World
from tota.things import Ancient, Hero, Creep, Tower
from tota.utils import closes_empty_position, distance
from tota import settings


def get_hero_function(name):
    module = __import__('tota.heroes.' + name, fromlist=['create', ])
    create_function = getattr(module, 'create')

    return create_function()


class Game:
    """An instance of game controls the flow of the game.

       This includes player and creeps spawning, game main loop, deciding when
       to stop, importing map data, drawing each update, etc.
    """
    def __init__(self, radiant_heroes, dire_heroes, map_file_path, world_size,
                 debug=False, use_basic_icons=False):
        self.radiant_heroes = radiant_heroes
        self.dire_heroes = dire_heroes
        self.map_file_path = map_file_path
        self.debug = debug
        self.use_basic_icons = use_basic_icons

        self.heroes = []
        self.ancients = {}

        self.world = World(world_size, debug=debug)

        self.initialize_world_map()
        self.cache_ancients()
        self.initialize_heroes()

    def initialize_world_map(self):
        with open(self.map_file_path, encoding='utf-8') as map_file:
            map_text = map_file.read()
            self.world.import_map(map_text)

    def cache_ancients(self):
        def get_ancient(team):
            ancients = [thing for thing in self.world.things.values()
                        if isinstance(thing, Ancient) and thing.team == team]
            if not ancients:
                message = "Can't find the ancient for the {} team".format(team)
                raise Exception(message)
            elif len(ancients) > 1:
                message = "Team {} has 2 ancients".format(team)
                raise Exception(message)
            else:
                return ancients[0]

        for team in (settings.TEAM_DIRE, settings.TEAM_RADIANT):
            self.ancients[team] = get_ancient(team)

    def initialize_heroes(self):
        teams = {
            settings.TEAM_DIRE: self.dire_heroes,
            settings.TEAM_RADIANT: self.radiant_heroes,
        }
        for team, heroes in teams.items():
            for hero_name in heroes:
                hero = Hero(name=hero_name,
                            team=team,
                            act_function=get_hero_function(hero_name))
                self.heroes.append(hero)
                self.spawn_near_ancient(hero)

    def spawn_near_ancient(self, thing):
        """Spawn players or creeps near their ancient."""
        # start searching from the ancient position, outwards, until an empty
        # space is found, using breadth first graph search
        ancient = self.ancients[thing.team]
        spawn_at = closes_empty_position(ancient, self.world)
        if spawn_at:
            self.world.spawn(thing, spawn_at)
        else:
            message = "Can't spawn {} near its ancient".format(thing.name)
            raise Exception(message)

    def position_draw(self, position):
        """Get the string to draw for a given position of the world."""
        # decorations first, then things over them
        thing = self.world.things.get(position)

        if thing is not None:
            if self.use_basic_icons:
                icon = thing.ICON_BASIC
            else:
                icon = thing.ICON
            return colored(icon, settings.TEAM_COLORS[thing.team])
        else:
            return ' '

    def play(self, frames_per_second=2.0):
        """Game main loop, ending in a game result with description."""
        while True:
            # spawn creep wave
            if self.world.t % settings.CREEP_WAVE_COOLDOWN == 0:
                for team in (settings.TEAM_RADIANT, settings.TEAM_DIRE):
                    for i in range(settings.CREEP_WAVE_SIZE):
                        creep = Creep(team)
                        self.spawn_near_ancient(creep)

            self.world.step()
            self.update_experience()
            self.clean_deads()

            # maintain the flow of zombies if necessary
            self.draw()

            if self.debug:
                input()
            else:
                time.sleep(1.0 / frames_per_second)

            if self.game_ended():
                description = self.game_result()
                print('')
                print(description)

                return description

    def update_experience(self):
        for thing in list(self.world.things.values()):
            if thing.life <= 0:
                for hero in self.heroes:
                    if distance(hero, thing) < settings.XP_DISTANCE:
                        if isinstance(thing, Creep):
                            hero.xp += settings.XP_CREEP_DEAD
                        elif isinstance(thing, Hero):
                            hero.xp += settings.XP_HERO_DEAD
                        elif isinstance(thing, Tower):
                            hero.xp += settings.XP_TOWER_DEAD

                self.world.destroy(thing)

    def clean_deads(self):
        """Remove dead things from the world."""
        for thing in list(self.world.things.values()):
            if thing.life <= 0:
                self.world.destroy(thing)

    def draw(self):
        """Draw the world."""
        screen = ''

        # print the world
        screen += '\n'.join(u''.join(self.position_draw((x, y)) + ' '
                                     for x in range(self.world.size[0]))
                            for y in range(self.world.size[1]))

        # game stats
        screen += '\nticks:{}'.format(self.world.t)

        # print hero stats
        for hero in sorted(self.heroes, key=lambda x: x.name):
            if hero.life > 0:
                # a small "health bar" with unicode chars, from 0 to 10 chars
                life_chars_count = int((10.0 / hero.max_life) * hero.life)
                life_chars = life_chars_count * '\u2588'
                no_life_chars = (10 - life_chars_count) * '\u2591'
                life_bar = '\u2665 {}{}'.format(life_chars, no_life_chars)
            else:
                life_bar = '\u2620 [dead]'

            hero_template = '{bar}({life}) {name} ({level})'
            hero_stats = hero_template.format(bar=life_bar,
                                              name=hero.name,
                                              life=int(hero.life),
                                              level=hero.level)

            screen += '\n' + colored(hero_stats,
                                     settings.TEAM_COLORS[hero.team])

        # print events (of last step) for debugging
        if self.debug:
            screen += u'\n'
            screen += u'\n'.join([colored('{}: {}'.format(thing.name, event),
                                          settings.TEAM_COLORS[thing.team])
                                  for t, thing, event in self.world.events
                                  if t == self.world.t])
        os.system('clear')
        print(screen)

    def destroyed_ancients(self):
        """Which ancients have been destroyed?"""
        return [ancient for ancient in self.ancients.values()
                if ancient.life <= 0]

    def game_ended(self):
        """Has the game ended?"""
        return len(self.destroyed_ancients()) > 0

    def game_result(self):
        """Was the game won?"""
        return '\n'.join('Team {} lost!'.format(ancient.team)
                         for ancient in self.destroyed_ancients())
