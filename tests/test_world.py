import unittest
from simulation import World
from sim_entities import Bot, Plant, StaticSignal


class TestParameterLimits(unittest.TestCase):
    def test_bot_limit(self):
        world = World(bot_limit=2)
        self.assertEqual(world.bot_limit, 2, 'Bot limit is not correctly set from parameter')
        self.assertEqual(len(world.bots), 0, 'World should start with zero bots')
        world.add_entity(Bot(0, 0, 1))
        self.assertEqual(len(world.bots), 1, "First bot is not added to the world's list of bots")
        world.add_entity(Bot(0, 1, 1))
        self.assertEqual(len(world.bots), 2, "Second bot is not added to world's list of bots")
        self.assertEqual(world.add_entity(Bot(0, 2, 1)), False, "Adding bots at the limit should return False")
        self.assertEqual(len(world.bots), 2, "Bots past the limit should not be appended to the world")

    def test_plant_limit(self):
        world = World(plant_limit=2)
        self.assertEqual(world.plant_limit, 2, 'Plant limit is not correctly set from parameter')
        self.assertEqual(len(world.plants), 0, 'World should start with zero plants')
        world.add_entity(Plant(0, 0, 1))
        self.assertEqual(len(world.plants), 1, "First plant is not added to the world's list of plants")
        world.add_entity(Plant(0, 1, 1))
        self.assertEqual(len(world.plants), 2, "Second plant is not added to world's list of plants")
        self.assertEqual(world.add_entity(Plant(0, 2, 1)), False, "Adding plants at the limit should return False")
        self.assertEqual(len(world.plants), 2, "Plants past the limit should not be appended to the world")

    def test_boundary_sizes_passed(self):
        bounded_world = World(boundary_sizes=(10, 2))
        self.assertEqual(bounded_world.boundary_sizes, (10, 2), "Boundary sizes are not assigned properly")
        self.assertEqual(bounded_world.half_boundaries, (5, 1), "Half boundaries are not assigned properly")
        world_no_bounds = World()
        self.assertEqual(world_no_bounds.boundary_sizes, None, "World with no parameter boundaries should not have any")
        self.assertEqual(world_no_bounds.half_boundaries, None, "Half bounds should be None if no world bounds")

    def test_energy_limit_parameter_processed(self):
        world = World(energy_pool=10)
        self.assertEqual(world.energy_pool, 10, "Energy pool limit is not assigned properly from parameter")
        self.assertEqual(world.initialized_energy, 10, "Initialized energy is not assigned properly")

    def test_no_energy_limits(self):
        world = World()
        self.assertEqual(world.energy_pool, None, "No energy pool should exist in a world without one set")
        self.assertEqual(world.initialized_energy, None, "Initialized energy should be None")


class TestWorldAddEntity(unittest.TestCase):
    def test_add_entity_with_zero_energy(self):
        world = World(energy_pool=10)
        plant = Plant(0, 0, 0)
        world.add_entity(plant)
        self.assertEqual(world.energy_pool, 10, "Adding an entity with 0 energy should not take from the energy pool")
        self.assertEqual(world.initialized_energy, 10, "Initialized energy should not alter")
        self.assertEqual(world.plants, [plant],
                         "Adding an entity with 0 energy should still be appended to its respective list")

    def test_add_entity_just_short_energy_limit(self):
        world = World(energy_pool=10)
        world.add_entity(Plant(0, 0, 9))
        self.assertEqual(world.energy_pool, 1, "Adding entities should drain energy from the energy pool")
        self.assertEqual(world.initialized_energy, 10, "Initialized energy should not alter")

    def test_add_entity_equal_energy_limit(self):
        world = World(energy_pool=10)
        world.add_entity(Plant(0, 0, 10))
        self.assertEqual(world.energy_pool, 0, "Consuming all energy from pool should leave zero remaining")
        self.assertEqual(world.initialized_energy, 10, "Initialized energy should not alter")

    def test_add_entity_above_energy_limit(self):
        world = World(energy_pool=10)
        self.assertEqual(world.add_entity(Plant(0, 0, 11)), False,
                         "Trying to add an entity with more energy in the pool should return False")
        self.assertEqual(len(world.plants), 0, "Plants should not be added if they require energy not available")
        self.assertEqual(world.energy_pool, 10, "Energy should not be consumed if no entity is added to world")
        self.assertEqual(world.initialized_energy, 10, "Initialized energy should not alter")

    def test_add_entity_negative_energy_with_energy_limit(self):
        world_with_limits = World(energy_pool=10)
        self.assertEqual(world_with_limits.add_entity(Plant(0, 0, -5)), False,
                         "Should not be able to add entity with negative energy with an energy pool")
        self.assertEqual(world_with_limits.initialized_energy, 10, "Initialized energy should not alter")

    def test_add_entity_negative_energy_without_world_limits(self):
        world_no_limits = World()
        self.assertEqual(world_no_limits.add_entity(Plant(0, 0, -5)), False,
                         "Should not be able to add entity with negative energy")


class TestWorldAggregateEntities(unittest.TestCase):
    def test_no_entities_added(self):
        world = World()
        world.aggregate_entities()
        self.assertEqual(world.all_entities, [], "Aggregated list should be empty with no entities in world")

    def test_add_single_entity(self):
        world = World()
        plant = Plant(0, 0, 1)
        world.add_entity(plant)
        world.aggregate_entities()
        self.assertEqual(world.all_entities, [plant],
                         "Adding an entity should result in it contained in the list of all entities")
        self.assertEqual(len(world.all_entities), 1, "List of all entities should be 1 if only 1 entity is added")

    def test_add_several_entities(self):
        world = World()
        plant = Plant(0, 0, 1)
        bot = Bot(0, 1, 2)
        signal = StaticSignal(0, 3, 2, bot)
        world.add_entity(plant)
        world.add_entity(bot)
        world.add_entity(signal)
        world.aggregate_entities()
        self.assertEqual(len(world.all_entities), 3, "List of all entities should be 3 when 3 have been added")
        self.assertIn(plant, world.all_entities, "The added plant should be in the list of all entities")
        self.assertIn(bot, world.all_entities, "The added bot should be in the list of all entities")
        self.assertIn(signal, world.all_entities, "The added signal should be in the list of all entities")

    def test_add_several_entities_and_remove_one(self):
        world = World()
        plant = Plant(0, 0, 1)
        bot = Bot(0, 1, 2)
        signal = StaticSignal(0, 3, 2, bot)
        world.add_entity(plant)
        world.add_entity(bot)
        world.add_entity(signal)
        world.aggregate_entities()
        world.plants = []
        world.aggregate_entities()
        self.assertEqual(len(world.all_entities), 2,
                         "List of all entities should be 2 when 3 have been added and 1 removed")
        self.assertNotIn(plant, world.all_entities, "The removed plant should no longer be in the list of all entities")
        self.assertIn(bot, world.all_entities, "The added bot should be in the list of all entities")
        self.assertIn(signal, world.all_entities, "The added signal should be in the list of all entities")


class TestWorldGiveEnergyToEntityWithEnergyPool(unittest.TestCase):
    def setUp(self):
        self.world = World(energy_pool=10)
        self.bot = Bot(0, 0, 0)
        self.world.add_entity(self.bot)

    def test_give_less_energy_than_energy_pool(self):
        self.assertTrue(self.world.give_energy_to_entity(5, self.bot),
                        "Should be able to give less energy than in the pool to an entity")
        self.assertEqual(self.bot.energy, 5, "An entity given 5 energy should have 5 more than before")
        self.assertEqual(self.world.energy_pool, 5,
                         "A world with 5 energy given to an entity should have 5 less energy than before")

    def test_give_as_much_energy_as_energy_pool(self):
        self.assertTrue(self.world.give_energy_to_entity(10, self.bot),
                        "Should be able to give all energy in pool to an entity")
        self.assertEqual(self.bot.energy, 10,
                         "An entity given all the energy in a world pool should have all the energy")
        self.assertEqual(self.world.energy_pool, 0,
                         "A world where all energy has been given to an entity should have 0 energy remaining")

    def test_give_more_energy_than_energy_pool(self):
        self.assertTrue(self.world.give_energy_to_entity(11, self.bot),
                        "Giving more energy to an entity than in the world pool should transfer remaining energy")
        self.assertEqual(self.bot.energy, 10,
                         "Attempting to give more energy to an entity than in the pool should transfer all energy")
        self.assertEqual(self.world.energy_pool, 0,
                         "Giving more energy than in the pool should drain the pool completely")

    def test_give_negative_energy_with_pool(self):
        self.assertFalse(self.world.give_energy_to_entity(-1, self.bot), "Should not be able to give negative energy")
        self.assertEqual(self.world.energy_pool, 10, "Energy pool should not change if a give attempt failed")

    def test_give_zero_energy_with_pool(self):
        self.assertTrue(self.world.give_energy_to_entity(0, self.bot),
                        "Giving zero energy with a pool should return True")
        self.assertEqual(self.world.energy_pool, 10, "Giving zero energy should not modify the world pool")
        self.assertEqual(self.bot.energy, 0, "Giving zero energy with a pool should not change entity energy")


class TestWorldGiveEnergyToEntityWithoutPool(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.bot = Bot(0, 0, 0)
        self.world.add_entity(self.bot)

    def test_give_energy_no_energy_pool(self):
        self.assertEqual(self.bot.energy, 0, "An entity initialized with 0 energy should have 0 energy")
        self.assertTrue(self.world.give_energy_to_entity(10, self.bot),
                        "Should be able to give energy to an entity without an energy pool")
        self.assertEqual(self.bot.energy, 10, "Entity should have 10 additional energy after being given 10")

    def test_give_negative_energy_without_pool(self):
        self.assertFalse(self.world.give_energy_to_entity(-1, self.bot),
                         "Should not be able to give negative energy even without an energy pool")

    def test_give_zero_energy_without_pool(self):
        self.assertTrue(self.world.give_energy_to_entity(0, self.bot),
                        "Giving zero energy without a pool should return True")
        self.assertEqual(self.bot.energy, 0,
                         "Giving zero energy without a pools to an entity should not change its energy")


class TestWorldDrainEnergyFromEntityWithoutPool(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.bot = Bot(0, 0, 10)
        self.world.add_entity(self.bot)

    def test_drain_negative_energy_without_pool(self):
        self.assertFalse(self.world.drain_energy_from_entity(-1, self.bot),
                         "Draining negative energy should not be allow")
        self.assertEqual(self.bot.energy, 10, "A failed drain should not remove energy")
        self.assertFalse(self.bot.dead, "A failed drain should not mark a living entity as dead")

    def test_drain_all_energy_without_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(10, self.bot),
                        "Draining all energy from an entity should be allowed")
        self.assertEqual(self.bot.energy, 0, "Draining all energy from an entity should leave it with zero energy")
        self.assertTrue(self.bot.dead, "Draining all energy from an entity should mark it as dead")

    def test_drain_some_energy_without_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(3, self.bot),
                        "Draining less than all of an entities energy should return True")
        self.assertEqual(self.bot.energy, 7,
                         "Draining less than all energy from an entity should leave a proper remainder")
        self.assertFalse(self.bot.dead, "Draining only some energy should not mark an entity as dead")

    def test_drain_no_energy_without_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(0, self.bot), "Draining 0 energy should be allowed")
        self.assertEqual(self.bot.energy, 10, "Draining no energy should not change entity energy level")
        self.assertFalse(self.bot.dead, "Draining no energy should not kill an entity with positive energy")

    def test_drain_too_much_energy_without_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(11, self.bot),
                        "Draining more energy than an entity has should be allowed (Drain all it has)")
        self.assertEqual(self.bot.energy, 0, "Draining more energy than an entity has should reduce it to 0 energy")
        self.assertTrue(self.bot.dead, "Draining more energy than an entity has should kill it")


class TestWorldDrainEnergyFromEntityWithPool(unittest.TestCase):
    def setUp(self):
        self.world = World(energy_pool=10)
        self.bot = Bot(0, 0, 3)
        self.world.add_entity(self.bot)

    def test_energy_in_pool_affected_by_entity_addition(self):
        self.assertEqual(self.world.energy_pool, 7, "Adding an entity with energy should be removed from the pool")
        self.assertEqual(self.world.initialized_energy, 10,
                         "Adding an entity with energy should not modify instantiated pool amount")

    def test_drain_negative_energy_with_pool(self):
        self.assertFalse(self.world.drain_energy_from_entity(-1, self.bot),
                         "Should not be able to drain negative energy")
        self.assertEqual(self.bot.energy, 3, "Failed draining should not modify entity energy")
        self.assertFalse(self.bot.dead, "Failed draining should not mark entity as dead")
        self.assertEqual(self.world.energy_pool, 7, "Failed draining should not return energy to the energy pool")
        self.assertEqual(self.world.initialized_energy, 10,
                         "Failed draining should not modify instantiated pool amount")

    def test_drain_all_energy_with_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(3, self.bot),
                        "Draining all energy from an entity should be allowed with a pool")
        self.assertEqual(self.bot.energy, 0,
                         "Draining all energy from an entity should reduce its energy to zero with a pool")
        self.assertTrue(self.bot.dead, "Removing all energy from an entity should kill it with an energy pool")
        self.assertEqual(self.world.energy_pool, 10,
                         "Removing all energy from an entity should restore all that energy to the energy pool")
        self.assertEqual(self.world.initialized_energy, 10,
                         "Draining all energy from an entity should not modify the instantiated pool amount")

    def test_drain_some_energy_with_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(2, self.bot),
                        "Draining some energy from an entity should be allowed with an energy pool")
        self.assertEqual(self.bot.energy, 1, "Draining some energy with a pool should result in a proper remainder")
        self.assertFalse(self.bot.dead, "Draining only some energy should not kill an entity with remaining energy")
        self.assertEqual(self.world.energy_pool, 9, "Draining some energy should return that energy to the pool")
        self.assertEqual(self.world.initialized_energy, 10,
                         "Draining some energy should not modify the instantiated pool amount")

    def test_drain_no_energy_with_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(0, self.bot),
                        "Draining no energy should be allowed with an energy pool")
        self.assertEqual(self.bot.energy, 3, "Draining no energy should not modify entity energy with a pool")
        self.assertFalse(self.bot.dead, "Draining no energy should not kill an entity with positive energy")
        self.assertEqual(self.world.energy_pool, 7, "Draining no energy should not modify the energy pool")
        self.assertEqual(self.world.initialized_energy, 10,
                         "Draining no energy should not modify the initialized energy amount")

    def test_drain_too_much_energy_with_pool(self):
        self.assertTrue(self.world.drain_energy_from_entity(5, self.bot),
                        "Draining more energy than an entity has should be allowed with a pool")
        self.assertEqual(self.bot.energy, 0, "Draining more energy than an entity has should reduce it to zero")
        self.assertTrue(self.bot.dead, "Draining more energy than an entity has should kill it")
        self.assertEqual(self.world.energy_pool, 10,
                         "Draining more energy than an entity has should not raise the pool past its initial amount")
        self.assertEqual(self.world.initialized_energy, 10,
                         "Draining more energy than an entity has should not modify the initialized energy amount")


class TestWorldTransferEnergyBetweenEntitiesDonorHasEnergy(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.donor = Bot(0, 0, 10)
        self.recipient = Bot(0, 1, 10)
        self.world.add_entity(self.donor)
        self.world.add_entity(self.recipient)

    def test_donor_has_energy_transfer_none(self):
        self.assertTrue(self.world.transfer_energy_between_entities(0, donor=self.donor, recipient=self.recipient),
                        "Transferring zero energy between entities should return true")
        self.assertEqual(self.donor.energy, 10, "Transferring zero energy should not alter the donor energy")
        self.assertEqual(self.recipient.energy, 10, "Transferring zero energy should not alter the recipient")
        self.assertFalse(self.donor.dead, "Transferring no energy should not kill a living donor")
        self.assertFalse(self.recipient.dead, "Transferring no energy should not kill a living recipient")

    def test_donor_has_energy_transfer_some(self):
        self.assertTrue(self.world.transfer_energy_between_entities(3, donor=self.donor, recipient=self.recipient),
                        "Transferring some energy between entities should be allowed")
        self.assertEqual(self.donor.energy, 7, "Donating energy in a transfer should reduce donor energy levels")
        self.assertEqual(self.recipient.energy, 13, "Receiving energy from a transfer should increase energy levels")
        self.assertFalse(self.donor.dead, "Transferring less energy than the donor has should not kill the donor")
        self.assertFalse(self.recipient.dead, "Transferring energy to a living recipient should not kill it")

    def test_donor_has_energy_transfer_all(self):
        self.assertTrue(self.world.transfer_energy_between_entities(10, donor=self.donor, recipient=self.recipient),
                        "Transferring all energy from a donor to a recipient should be allowed")
        self.assertEqual(self.donor.energy, 0, "Transferring all energy from donor should leave it with zero energy")
        self.assertEqual(self.recipient.energy, 20,
                         "Receiving all energy from a transfer should result in an appropriate increase")
        self.assertTrue(self.donor.dead, "Transferring all energy from a donor should kill it")
        self.assertFalse(self.recipient.dead, "Receiving all energy from a donor should not kill a living recipient")

    def test_donor_has_energy_transfer_too_much(self):
        self.assertTrue(self.world.transfer_energy_between_entities(11, donor=self.donor, recipient=self.recipient),
                        "Transferring more energy than a donor has should return True (transfer all available energy)")
        self.assertEqual(self.donor.energy, 0, "Transferring more energy than a donor has should reduce it to zero")
        self.assertEqual(self.recipient.energy, 20, "Transferring more energy than a donor has should only increase \
        recipient energy by donor total")
        self.assertTrue(self.donor.dead, "Transferring more energy than a donor has should kill it")
        self.assertFalse(self.recipient.dead, "Transferring more energy than a donor has should not kill the recipient")


class TestWorldTransferEnergyBetweenEntitiesDonorDoesNotHaveEnergy(unittest.TestCase):
    def setUp(self):
        self.world = World()
        self.donor = Bot(0, 0, 0)
        self.recipient = Bot(0, 0, 10)
        self.world.add_entity(self.donor)
        self.world.add_entity(self.recipient)

    def test_donor_has_no_energy_transfer_none(self):
        # TODO: Decide if it's appropriate to return true if no energy is transferred
        self.assertTrue(self.world.transfer_energy_between_entities(0, donor=self.donor, recipient=self.recipient),
                        "Transferring no energy from a donor with no energy should be allowed")
        self.assertEqual(self.donor.energy, 0,
                         "Transferring no energy from a donor with no energy should leave it with no energy")
        self.assertEqual(self.recipient.energy, 10,
                         "Transferring no energy from an entity with no energy should not modify recipient energy")
        self.assertTrue(self.donor.dead, "Transferring no energy from an entity with no energy should kill it")
        self.assertFalse(self.recipient.dead,
                         "Transferring no energy from an entity with no energy should not kill a living recipient")

    def test_donor_has_no_energy_transfer_some(self):
        # TODO: Decide if returning True makes sense when the requested amount was not transferred
        self.assertTrue(self.world.transfer_energy_between_entities(1, donor=self.donor, recipient=self.recipient),
                        "Transferring energy should be allowed")
        self.assertEqual(self.donor.energy, 0, "Transferring energy from a donor with none should keep it at zero")
        self.assertEqual(self.recipient.energy, 10,
                         "Transferring energy from a donor with none should not modify the recipient")
        self.assertTrue(self.donor.dead, "Transferring energy from a donor with none should kill it")
        self.assertFalse(self.recipient.dead,
                         "Transferring energy from a donor with none should not kill the recipient")


class TestWorldTransferEnergyBetweenEntitiesToDeadEntity(unittest.TestCase):
    def test_transfer_energy_to_dead_recipient(self):
        world = World()
        donor = Bot(0, 0, 10)
        recipient = Bot(0, 0, 0)
        world.add_entity(donor)
        world.add_entity(recipient)
        recipient.dead = True
        self.assertFalse(world.transfer_energy_between_entities(1, donor=donor, recipient=recipient),
                         "Transferring energy to a dead recipient should not be allowed")
        self.assertEqual(donor.energy, 10, "Transferring energy to a dead recipient should not modify donor levels")
        self.assertEqual(recipient.energy, 0, "Transferring energy to a dead recipient should keep it at zero energy")
        self.assertFalse(donor.dead, "Transferring energy to a dead recipient should not kill the living donor")
        self.assertTrue(recipient.dead, "Transferring energy to a dead recipient should keep it dead")

    def test_transfer_energy_from_dead_donor(self):
        world = World()
        donor = Bot(0, 0, 0)
        recipient = Bot(0, 0, 10)
        world.add_entity(donor)
        world.add_entity(recipient)
        donor.dead = True
        self.assertFalse(world.transfer_energy_between_entities(1, donor=donor, recipient=recipient),
                         "Transferring energy from a dead donor should not be allowed")
        self.assertEqual(donor.energy, 0, "Transferring energy from a dead donor should keep its energy at zero")
        self.assertEqual(recipient.energy, 10, "Transferring energy from a dead donor should not modify the recipient")
        self.assertTrue(donor.dead, "Transferring energy from a dead donor should keep it dead")
        self.assertFalse(recipient.dead, "Transferring energy from a dead donor should keep a living recipient alive")


class TestWorldGetUnitVectorWithoutBounds(unittest.TestCase):
    def setUp(self):
        self.world = World()

    def test_get_unit_vector_north(self):
        unit_vector = self.world.get_unit_vector_to_point((0, 0), (0, 1))
        self.assertEqual(unit_vector, (0, 1))

    def test_get_unit_vector_south_west(self):
        unit_vector = self.world.get_unit_vector_to_point((0, 0), (-1, -1))
        self.assertAlmostEqual(unit_vector[0], -0.7071, delta=0.01)
        self.assertAlmostEqual(unit_vector[1], -0.7071, delta=0.01)

    # TODO: Unit test the other quadrants


class TestWorldGetUnitVectorWithBounds(unittest.TestCase):
    def setUp(self):
        self.world = World(boundary_sizes=(10, 10))

    def test_get_unit_vector_north_not_through_boundary(self):
        unit_vector = self.world.get_unit_vector_to_point((5, 5), (5, 6))
        self.assertEqual(unit_vector, (0, 1))

    def test_get_unit_vector_north_through_boundary(self):
        unit_vector = self.world.get_unit_vector_to_point((5, 8), (5, 0))
        self.assertEqual(unit_vector, (0, 1))

    # TODO: Unit test the other boundaries


# TODO: Unit test the step method from World