from operator import or_
import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.data import race_townhalls


class LingAllIn(sc2.BotAI):
    def __init__(self):
        self.cheese_done = False
        self.fourteen_overlord = False
        self.extractor_trick_started = False
        self.extractor_trick_finished = False
        self.hatch_started = False
        self.workers_to_gas = False
        self.drone_sent = False
        self.hatch_drone = None
        self.nat_location = None
        self.real_gas = False
        self.pool_started = False
        self.gas_carriers = []
        self.queen_started = False
        self.pool_lord = False
        self.main_hatch = None
        self.rally_set = False

    def select_target(self):
        return self.enemy_structures.random_or(self.enemy_start_locations[0]).position

    async def on_step(self, iteration=0):
        if iteration == 0:
            self.main_hatch = self.townhalls[0]
        larvae = self.units(LARVA)
        forces = self.units(ZERGLING)
        supply = self.supply_used

        for queen in self.units(QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                self.do(queen(AbilityId.EFFECT_INJECTLARVA, self.structures(HATCHERY).closest_to(queen.position)))

        idle_drones = self.workers.idle
        for drone in idle_drones:
            target_field = self.mineral_field.closest_to(drone.position)
            self.do(drone.gather(target_field))

        if not self.cheese_done:
            if len(self.townhalls) == 2 and not self.rally_set:
                for hatch in self.townhalls:
                    self.do(hatch(RALLY_HATCHERY_UNITS, self.nat_location.to2.towards(self.game_info.map_center, 5)))
                    self.rally_set = True

            if supply == 27:
                if len(larvae) > 0 and self.minerals >= 100:
                    self.train(OVERLORD)
                    return

            if supply < 14:
                self.train(DRONE)
                return

            if not self.extractor_trick_started and supply == 14:
                if self.can_afford(EXTRACTOR):
                    drone = self.workers.random
                    target = self.vespene_geyser.closest_to(drone.position)
                    err = self.do(drone.build(EXTRACTOR, target))
                    self.extractor_trick_started = True
                    return

            if self.extractor_trick_started and not self.extractor_trick_finished:
                target = self.structures(EXTRACTOR).not_ready
                if len(target) > 0:
                    self.do(target[0](CANCEL))
                    self.extractor_trick_finished = True
                    return

            if self.extractor_trick_finished and not self.drone_sent and self.minerals >= 200 and not self.hatch_started:
                if not self.hatch_drone:
                    self.hatch_drone = self.workers.random
                self.nat_location = await self.get_next_expansion()
                self.drone_sent = True
                self.do(self.hatch_drone.move(self.nat_location))
                return

            if self.drone_sent and not self.hatch_started:
                if self.minerals >= 300:
                    self.do(self.hatch_drone.build(HATCHERY, self.nat_location))
                    self.hatch_started = True
                    return

            if self.hatch_started and self.minerals >= 140 and not self.real_gas:
                drone = self.workers.random
                target = self.vespene_geyser.closest_to(drone.position)
                err = self.do(drone.build(EXTRACTOR, target))
                self.real_gas = True
                return

            if self.real_gas and not self.pool_started:
                if self.minerals >= 200:
                    drone = self.workers.random
                    pool_location = self.main_hatch.position.to2.towards(self.game_info.map_center, 7)
                    self.do(drone.build(SPAWNINGPOOL, pool_location))
                    self.pool_started = True
                    return

            if self.pool_started and not self.pool_lord:
                if self.minerals >= 100:
                    self.train(OVERLORD)
                    self.pool_lord = True
                    return

            if self.real_gas and not self.workers_to_gas:
                target_gas = self.structures(EXTRACTOR).ready
                if len(target_gas) > 0:
                    gas_miners = self.workers.random_group_of(3)
                    for drone in gas_miners:
                        self.do(drone.gather(target_gas[0]))
                    self.workers_to_gas = True
                    return

            if self.vespene >= 88:
                for drone in self.workers:
                    if drone.is_carrying_vespene:
                        self.gas_carriers.append(drone)

            if len(self.gas_carriers) > 0:
                for drone in self.gas_carriers:
                    self.do(drone.return_resource())
                    self.do(drone.move(self.nat_location, queue=True))
                    self.gas_carriers.pop(self.gas_carriers.index(drone))

            if self.vespene >= 100 and self.structures(SPAWNINGPOOL).ready:
                self.research(ZERGLINGMOVEMENTSPEED)
                return

            if self.structures(SPAWNINGPOOL).ready and not self.queen_started:
                if self.minerals >= 150:
                    self.do(self.townhalls[0].train(QUEEN))
                    self.queen_started = True
                    return

            if self.queen_started:
                if len(larvae) > 0:
                    if self.minerals >= 50:
                        self.train(ZERGLING)
                        return

            if len(self.units(ZERGLING)) >= 24:
                self.cheese_done = True
                return

        if self.cheese_done:
            for ling in forces:
                self.do(ling.attack(self.select_target()))

            if self.minerals >= 50:
                if len(larvae) > 0:
                    self.train(ZERGLING)
                    return

            if self.supply_used - supply <= 2:
                if larvae and self.minerals >= 100:
                    self.train(OVERLORD)
                    return



def main():
    sc2.run_game(
        sc2.maps.get("KairosJunctionLE"),
        [Bot(Race.Zerg, LingAllIn()), Computer(Race.Zerg, Difficulty.VeryHard)],
        realtime=False,
        save_replay_as="AntonReplayElite.SC2Replay",
    )


if __name__ == '__main__':
    main()
