#need to clean up imports, a bunch aren't used
from operator import or_
import random
import numpy as np
import sc2
from sc2 import Race, Difficulty
from sc2.data import Alert
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.player import Bot, Computer

class LQNBot(sc2.BotAI):
    def __init__(self):
        self.rally_set = False
        self.build_order_done = False
        self.thirteen_overlord = False
        self.nat_location = None
        self.drone_sent = False
        self.hatch_drone = None
        self.hatch_started = False
        self.real_gas = False
        self.drones_to_gas = False
        self.pool_started = False
        self.nineteen_overlord = False
        self.queen_one = False
        self.queen_two = False
        self.speed_started = False
        self.defense_lings = False
        self.lair = False
        self.nydus_network = False
        self.queen_three = False
        self.main_hatch = None
        self.main_height = None
        self.x_mod = 0
        self.nydus_spotter = None

    def select_target(self):
        return self.enemy_structures.random_or(self.enemy_start_locations[0]).position

    def calculate_overlord_position(self, my_main, enemy_main):
        my_x = my_main[0]
        en_x, en_y = enemy_main[0], enemy_main[1]
        if my_x - en_x > 0:
            self.x_mod = 1
        else:
            self.x_mod = -1
        x = en_x + (self.x_mod * 25)
        location = (x, en_y)
        return Point2(location)

    async def on_step(self, iteration):
        if iteration == 0:
            self.main_hatch = self.townhalls[0]
            self.main_height = self.get_terrain_z_height(self.main_hatch.position)
            overlord_spot = self.calculate_overlord_position(self.townhalls[0].position, self.enemy_start_locations[0])
            self.nydus_spotter = self.units(UnitTypeId.OVERLORD).first
            self.do(self.nydus_spotter.move(overlord_spot))
        larvae = len(self.units(UnitTypeId.LARVA))
        supply = self.supply_used

        if not self.rally_set and len(self.townhalls) > 1:
            for hq in self.townhalls:
                self.do(hq(AbilityId.RALLY_HATCHERY_UNITS, self.nat_location.to2.towards(self.game_info.map_center, 5)))
                self.rally_set = True

        if self.already_pending(UnitTypeId.NYDUSNETWORK):
            self.build_order_done = True

        for queen in self.units(UnitTypeId.QUEEN).idle:
            abilities = await self.get_available_abilities(queen)
            if AbilityId.EFFECT_INJECTLARVA in abilities:
                self.do(queen(
                    AbilityId.EFFECT_INJECTLARVA, self.townhalls.closest_to(queen.position)))

        if not self.build_order_done:
            for extract in self.gas_buildings:
                if extract.assigned_harvesters < extract.ideal_harvesters:
                    w = self.workers.closer_than(20, extract)
                    if w.exists:
                        self.do(w.random.gather(extract))

            for hq in self.townhalls:
                if hq.assigned_harvesters > hq.ideal_harvesters:
                    await self.distribute_workers()

            if supply == 12:
                if self.can_afford(UnitTypeId.DRONE) and larvae > 0:
                    self.train(UnitTypeId.DRONE)
                    return

            if not self.thirteen_overlord and supply == 13:
                if self.can_afford(UnitTypeId.OVERLORD) and larvae > 0:
                    self.train(UnitTypeId.OVERLORD)
                    self.thirteen_overlord = True
                    return
                else:
                    return

            if self.thirteen_overlord and supply < 15:
                if self.can_afford(UnitTypeId.DRONE) and larvae > 0:
                    self.train(UnitTypeId.DRONE)
                    return

            if not self.drone_sent and self.minerals >= 200:
                self.nat_location = await self.get_next_expansion()
                self.hatch_drone = self.workers.random
                self.do(self.hatch_drone.move(self.nat_location))
                self.drone_sent = True
                return

            if self.drone_sent and not self.hatch_started:
                if self.minerals >= 300:
                    self.do(self.hatch_drone.build(UnitTypeId.HATCHERY, self.nat_location))
                    self.hatch_started = True
                    return
                else:
                    return

            if self.hatch_started and not self.real_gas and supply < 16:
                if self.can_afford(UnitTypeId.DRONE) and larvae > 0:
                    self.train(UnitTypeId.DRONE)
                    return

            if not self.real_gas and supply == 16:
                if self.can_afford(UnitTypeId.EXTRACTOR):
                    gas_drone = self.workers.random
                    target = self.vespene_geyser.closest_to(gas_drone.position)
                    self.do(gas_drone.build(UnitTypeId.EXTRACTOR, target))
                    self.real_gas = True
                    return
                else:
                    return

            if not self.pool_started and self.real_gas:
                if self.can_afford(UnitTypeId.SPAWNINGPOOL):
                    pos = self.main_hatch.position.to2.towards(self.game_info.map_center, 5)
                    drone = self.workers.random
                    self.do(drone.build(UnitTypeId.SPAWNINGPOOL, pos))
                    self.pool_started = True
                else:
                    return

            if self.pool_started and supply < 22:
                if supply == 19:
                    cocoons = self.units(UnitTypeId.OVERLORDCOCOON)
                    if cocoons:
                        if larvae > 0 and self.can_afford(UnitTypeId.OVERLORD):
                            self.train(UnitTypeId.OVERLORD)
                            return
                if larvae > 0 and self.can_afford(UnitTypeId.DRONE):
                    self.train(UnitTypeId.DRONE)
                    return

            if supply == 22:
                if self.minerals >= 300:
                    self.train(UnitTypeId.QUEEN)
                    self.train(UnitTypeId.QUEEN)
                    return
                else:
                    return

            if self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0 and self.can_afford(
                UpgradeId.ZERGLINGMOVEMENTSPEED
            ):
                spawning_pools_ready = self.structures(UnitTypeId.SPAWNINGPOOL).ready
                if spawning_pools_ready:
                    self.research(UpgradeId.ZERGLINGMOVEMENTSPEED)
                    self.speed_started = True
                    return

            if not self.lair and self.speed_started:
                if self.vespene >= 80:
                    if self.can_afford(UnitTypeId.LAIR):
                        for hq in self.townhalls:
                            if hq.is_idle:
                                self.do(hq.build(UnitTypeId.LAIR))
                                self.lair = True
                                return
                    else:
                        return

            if self.townhalls(UnitTypeId.LAIR).ready.exists and not self.already_pending(UnitTypeId.NYDUSNETWORK):
                if self.vespene >= 100:
                    if self.can_afford(UnitTypeId.NYDUSNETWORK):
                        drone = self.workers.random
                        hatch_pos = self.main_hatch.position
                        for i in range(-5, -10, -1):
                            network_pos = Point2((hatch_pos[0] + self.x_mod * i, hatch_pos[1]))
                            self.do(drone.build(UnitTypeId.NYDUSNETWORK, network_pos))
                    else:
                        return

        if self.structures(UnitTypeId.NYDUSNETWORK).ready.exists and not self.already_pending(UnitTypeId.NYDUSCANAL):
            if self.minerals >= 50:
                closest_ovie = self.units(UnitTypeId.OVERLORD).closest_to(self.enemy_start_locations[0].position)
                for i in range(11):
                    pos = closest_ovie.position.to2.towards(self.enemy_start_locations[0].position, i)
                    #debugger is saying i is referenced before being assigned in line 200
                    if self.get_terrain_z_height(pos) == self.main_height and self.is_visible(pos)\
                            and self.can_place(self.structures(UnitTypeId.NYDUSCANAL)):
                        nydus = self.structures(UnitTypeId.NYDUSNETWORK).ready[0]
                        self.do(nydus(AbilityId.BUILD_NYDUSWORM, pos))
                        return
            else:
                return

        if self.supply_left <= 2:
            cocoons = self.units(UnitTypeId.OVERLORDCOCOON)
            if cocoons:
                pass
            else:
                if larvae > 0 and self.can_afford(UnitTypeId.OVERLORD):
                    self.train(UnitTypeId.OVERLORD)

        if self.structures(UnitTypeId.SPAWNINGPOOL).ready.exists:
            if self.can_afford(UnitTypeId.ZERGLING) and larvae > 0:
                self.train(UnitTypeId.ZERGLING)
                return
            if self.can_afford(UnitTypeId.QUEEN) and self.build_order_done:
                self.train(UnitTypeId.QUEEN)
                return


def main():
    sc2.run_game(
        sc2.maps.get("KairosJunctionLE"),
        [Bot(Race.Zerg, LQNBot()), Computer(Race.Zerg, Difficulty.VeryEasy)],
        realtime=False,
        save_replay_as="LQNPart1.SC2Replay"
    )


if __name__ == '__main__':
    main()
