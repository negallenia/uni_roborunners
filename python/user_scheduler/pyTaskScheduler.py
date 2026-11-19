





"""

#pyTaskScheduler.py — Default naive Python Task Scheduler.
#Greedily assigns unassigned tasks to free agents in iteration order.

import MAPF


class pyTaskScheduler:
    def __init__(self):
        self.env = None
        self.free_agents = set()
        self.free_tasks = set()

    def initialize(self, preprocess_time_limit: int):
        pass
        """

# Manhattan Distance-aware task scheduler
# Auction-based assignment (my credits to open source, it is based on  https://github.com/Marcos-C7/Auction-algorithm)

from array import array
from collections import deque
import heapq
import time


class pyTaskScheduler:
    def __init__(self):
        self.env = None
        self._rows = 0
        self._cols = 0
        self._free = []
        self._neighbors = []
        self._distances = {}
        self._distance_typecode = "H"
        self._unreachable = 65535
        self._route_costs = {}

    def initialize(self, preprocess_time_limit: int):
        self._rows = self.env.rows
        self._cols = self.env.cols
        cell_count = self._rows * self._cols
        self._free = [cell == 0 for cell in self.env.map]
        self._neighbors = [[] for _ in range(cell_count)]

        for loc, is_free in enumerate(self._free):
            if not is_free:
                continue
            row, col = divmod(loc, self._cols)
            neighbors = self._neighbors[loc]
            if row > 0 and self._free[loc - self._cols]:
                neighbors.append(loc - self._cols)
            if row + 1 < self._rows and self._free[loc + self._cols]:
                neighbors.append(loc + self._cols)
            if col > 0 and self._free[loc - 1]:
                neighbors.append(loc - 1)
            if col + 1 < self._cols and self._free[loc + 1]:
                neighbors.append(loc + 1)

        if cell_count > self._unreachable:
            self._distance_typecode = "I"
            self._unreachable = 4294967295

        self._distances.clear()
        self._route_costs.clear()

        free_cells = [loc for loc, is_free in enumerate(self._free) if is_free]
        preferred_sources = []
        for states in (self.env.start_states, self.env.curr_states):
            for state in states:
                if 0 <= state.location < cell_count and self._free[state.location]:
                    preferred_sources.append(state.location)

        preprocess_seconds = max(0.0, preprocess_time_limit / 1000.0)
        cache_seconds = min(8.0, preprocess_seconds * 0.4)
        deadline = time.monotonic() + cache_seconds
        seen_sources = set()
        for source in preferred_sources + free_cells:
            if source in seen_sources:
                continue
            seen_sources.add(source)
            if time.monotonic() >= deadline:
                break
            self._compute_distances(source)

    def _compute_distances(self, source: int):
        if source in self._distances:
            return self._distances[source]
        if source < 0 or source >= len(self._free) or not self._free[source]:
            return None

        distances = array(self._distance_typecode, [self._unreachable]) * len(self._free)
        distances[source] = 0
        queue = deque([source])
        neighbors = self._neighbors
        while queue:
            current = queue.popleft()
            next_distance = distances[current] + 1
            for neighbor in neighbors[current]:
                if distances[neighbor] == self._unreachable:
                    distances[neighbor] = next_distance
                    queue.append(neighbor)

        self._distances[source] = distances
        return distances

    def _distance(self, source: int, target: int, deadline: float) -> int:
        if (
            source < 0
            or target < 0
            or source >= len(self._free)
            or target >= len(self._free)
            or not self._free[source]
            or not self._free[target]
        ):
            return self._unreachable

        distances = self._distances.get(source)
        if distances is None and time.monotonic() < deadline:
            distances = self._compute_distances(source)
        if distances is not None:
            return distances[target]

        source_row, source_col = divmod(source, self._cols)
        target_row, target_col = divmod(target, self._cols)
        return abs(source_row - target_row) + abs(source_col - target_col)

    def _route_cost(self, task_id: int, task, deadline: float) -> int:
        locations = tuple(task.locations)
        next_location = task.idx_next_loc
        cache_key = (task_id, next_location)
        cached = self._route_costs.get(cache_key)
        if cached is not None:
            return cached

        remaining = locations[next_location:]
        if not remaining:
            return self._unreachable

        cost = len(remaining)
        exact = True
        for first, second in zip(remaining, remaining[1:]):
            if first not in self._distances and time.monotonic() >= deadline:
                exact = False
            distance = self._distance(first, second, deadline)
            if distance == self._unreachable:
                return self._unreachable
            cost += distance

        if exact:
            self._route_costs[cache_key] = cost
        return cost

    """
    Legacy minimum-cost-flow implementation, retained for reference.

    @staticmethod
    def _add_edge(graph, source: int, target: int, capacity: int, cost: int):
        forward = [target, len(graph[target]), capacity, cost]
        reverse = [source, len(graph[source]), 0, -cost]
        graph[source].append(forward)
        graph[target].append(reverse)

    def _minimum_cost_matching(self, agents, task_ids, candidate_edges, deadline):
        agent_count = len(agents)
        task_count = len(task_ids)
        source = 0
        first_agent = 1
        first_task = first_agent + agent_count
        sink = first_task + task_count
        graph = [[] for _ in range(sink + 1)]

        task_index = {task_id: index for index, task_id in enumerate(task_ids)}
        for agent_index in range(agent_count):
            self._add_edge(graph, source, first_agent + agent_index, 1, 0)
        for task_index_value in range(task_count):
            self._add_edge(graph, first_task + task_index_value, sink, 1, 0)

        for agent_index, edges in enumerate(candidate_edges):
            node = first_agent + agent_index
            for cost, task_id in edges:
                self._add_edge(
                    graph,
                    node,
                    first_task + task_index[task_id],
                    1,
                    cost,
                )

        node_count = len(graph)
        potentials = [0] * node_count
        infinity = self._unreachable * max(1, node_count)
        flow = 0

        while flow < min(agent_count, task_count) and time.monotonic() < deadline:
            distances = [infinity] * node_count
            previous_node = [-1] * node_count
            previous_edge = [-1] * node_count
            distances[source] = 0
            queue = [(0, source)]

            while queue:
                current_distance, current = heapq.heappop(queue)
                if current_distance != distances[current]:
                    continue

                for edge_index, edge in enumerate(graph[current]):
                    if edge[2] == 0:
                        continue
                    next_node = edge[0]
                    next_distance = (
                        current_distance
                        + edge[3]
                        + potentials[current]
                        - potentials[next_node]
                    )
                    if next_distance < distances[next_node]:
                        distances[next_node] = next_distance
                        previous_node[next_node] = current
                        previous_edge[next_node] = edge_index
                        heapq.heappush(queue, (next_distance, next_node))

            if previous_node[sink] == -1:
                break

            for node, distance in enumerate(distances):
                if distance < infinity:
                    potentials[node] += distance

            node = sink
            while node != source:
                previous = previous_node[node]
                edge = graph[previous][previous_edge[node]]
                edge[2] -= 1
                graph[node][edge[1]][2] += 1
                node = previous
            flow += 1

        assignment = {}
        for agent_index, agent_id in enumerate(agents):
            node = first_agent + agent_index
            for edge in graph[node]:
                if first_task <= edge[0] < sink and edge[2] == 0:
                    task_id = task_ids[edge[0] - first_task]
                    assignment[agent_id] = task_id
                    break
        return assignment, flow

    def plan(self, time_limit: int) -> list:
        schedule = list(self.env.curr_task_schedule)
        agent_count = self.env.num_of_agents
        if len(schedule) != agent_count:
            schedule = [-1] * agent_count

        for agent_id, task_id in enumerate(schedule):
            if task_id != -1 and task_id not in self.env.task_pool:
                schedule[agent_id] = -1

        agents = [agent_id for agent_id, task_id in enumerate(schedule) if task_id == -1]
        if not agents:
            return schedule

        tasks = []
        task_objects = {}
        for task_id in self.env.task_pool:
            task = self.env.task_pool[task_id]
            if (
                task.idx_next_loc == 0
                and task.agent_assigned == -1
                and task.locations
            ):
                tasks.append(task_id)
                task_objects[task_id] = task

        if not tasks:
            return schedule

        start = time.monotonic()
        planning_seconds = max(0.0, time_limit / 1000.0)
        has_active_assignments = any(task_id != -1 for task_id in schedule)
        if has_active_assignments:
            scheduler_budget = min(0.03, planning_seconds * 0.03)
        else:
            scheduler_budget = min(0.2, planning_seconds * 0.2)
        deadline = start + scheduler_budget

        route_costs = {}
        usable_tasks = []
        for task_id in tasks:
            route_cost = self._route_cost(task_id, task_objects[task_id], deadline)
            if route_cost < self._unreachable:
                usable_tasks.append(task_id)
                route_costs[task_id] = route_cost
        tasks = usable_tasks
        if not tasks:
            return schedule

        states = self.env.curr_states
        candidate_edges = []
        candidate_limit = min(64, len(tasks))
        for agent_id in agents:
            if agent_id >= len(states):
                candidate_edges.append([])
                continue
            location = states[agent_id].location

            def choices():
                for task_id in tasks:
                    task = task_objects[task_id]
                    first_goal = task.locations[task.idx_next_loc]
                    distance = self._distance(location, first_goal, deadline)
                    if distance >= self._unreachable:
                        continue
                    cost = distance + route_costs[task_id]
                    yield cost, task_id

            candidate_edges.append(
                heapq.nsmallest(candidate_limit, choices())
            )

        matching_width = min(16, candidate_limit)
        assignment, flow = self._minimum_cost_matching(
            agents,
            tasks,
            [edges[:matching_width] for edges in candidate_edges],
            deadline,
        )

        target_flow = min(len(agents), len(tasks))
        while flow < target_flow and matching_width < candidate_limit:
            if time.monotonic() >= deadline:
                break
            matching_width = min(candidate_limit, matching_width * 2)
            assignment, flow = self._minimum_cost_matching(
                agents,
                tasks,
                [edges[:matching_width] for edges in candidate_edges],
                deadline,
            )

        if flow < target_flow:
            used_tasks = set(assignment.values())
            remaining_edges = []
            for agent_index, agent_id in enumerate(agents):
                if agent_id in assignment:
                    continue
                for cost, task_id in candidate_edges[agent_index]:
                    if task_id not in used_tasks:
                        remaining_edges.append((cost, agent_id, task_id))
            remaining_edges.sort()
            used_agents = set(assignment)
            for _, agent_id, task_id in remaining_edges:
                if agent_id not in used_agents and task_id not in used_tasks:
                    assignment[agent_id] = task_id
                    used_agents.add(agent_id)
                    used_tasks.add(task_id)

        for agent_id, task_id in assignment.items():
            schedule[agent_id] = task_id
        return schedule
    """

    def _epsilon_auction(self, agents, task_ids, candidate_edges, deadline):
        agent_count = len(agents)
        if agent_count == 0:
            return {}

        task_index = {task_id: index for index, task_id in enumerate(task_ids)}
        max_cost = max(
            (cost for edges in candidate_edges for cost, _ in edges),
            default=0,
        )
        # Private dummy items let agents remain unassigned without blocking others.
        dummy_penalty = (max_cost + 1) * (agent_count + 1)
        item_count = len(task_ids) + agent_count
        prices = [0.0] * item_count
        item_owner = [-1] * item_count
        # This is below 1/n, so a completed auction is optimal for integer costs.
        epsilon = 1.0 / (agent_count + 1)

        choices = []
        for agent_index, edges in enumerate(candidate_edges):
            agent_choices = [
                (task_index[task_id], -cost) for cost, task_id in edges
            ]
            agent_choices.append(
                (len(task_ids) + agent_index, -dummy_penalty)
            )
            choices.append(agent_choices)

        unassigned = deque(range(agent_count))
        while unassigned and time.monotonic() < deadline:
            agent_index = unassigned.popleft()
            best_item = -1
            best_value = float("-inf")
            second_value = float("-inf")

            for item, value in choices[agent_index]:
                net_value = value - prices[item]
                if (
                    net_value > best_value
                    or (net_value == best_value and item < best_item)
                ):
                    second_value = best_value
                    best_value = net_value
                    best_item = item
                elif net_value > second_value:
                    second_value = net_value

            if best_item == -1:
                continue
            if second_value == float("-inf"):
                second_value = best_value - epsilon

            prices[best_item] += best_value - second_value + epsilon
            previous_owner = item_owner[best_item]
            item_owner[best_item] = agent_index

            if previous_owner != -1:
                unassigned.append(previous_owner)

        assignment = {}
        if not unassigned:
            for item, agent_index in enumerate(item_owner[:len(task_ids)]):
                if agent_index != -1:
                    assignment[agents[agent_index]] = task_ids[item]

        # If the deadline interrupts the auction, construct a valid schedule
        # from scratch rather than keeping a partial assignment that blocks
        # an augmenting reassignment.
        used_agents = set(assignment)
        used_tasks = set(assignment.values())
        remaining_pairs = []
        for agent_index, edges in enumerate(candidate_edges):
            agent_id = agents[agent_index]
            if agent_id in used_agents:
                continue
            for cost, task_id in edges:
                if task_id not in used_tasks:
                    remaining_pairs.append((cost, agent_id, task_id))
        remaining_pairs.sort()
        for _, agent_id, task_id in remaining_pairs:
            if agent_id not in used_agents and task_id not in used_tasks:
                assignment[agent_id] = task_id
                used_agents.add(agent_id)
                used_tasks.add(task_id)

        return assignment

    def plan(self, time_limit: int) -> list:
        schedule = list(self.env.curr_task_schedule)
        agent_count = self.env.num_of_agents
        if len(schedule) != agent_count:
            schedule = [-1] * agent_count

        for agent_id, task_id in enumerate(schedule):
            if task_id != -1 and task_id not in self.env.task_pool:
                schedule[agent_id] = -1

        agents = [agent_id for agent_id, task_id in enumerate(schedule) if task_id == -1]
        if not agents:
            return schedule

        tasks = []
        task_objects = {}
        for task_id in self.env.task_pool:
            task = self.env.task_pool[task_id]
            if (
                task.idx_next_loc == 0
                and task.agent_assigned == -1
                and task.locations
            ):
                tasks.append(task_id)
                task_objects[task_id] = task

        if not tasks:
            return schedule

        start = time.monotonic()
        planning_seconds = max(0.0, time_limit / 1000.0)
        has_active_assignments = any(task_id != -1 for task_id in schedule)
        if has_active_assignments:
            scheduler_budget = min(0.03, planning_seconds * 0.03)
        else:
            scheduler_budget = min(0.2, planning_seconds * 0.2)
        deadline = start + scheduler_budget

        route_costs = {}
        usable_tasks = []
        for task_id in tasks:
            route_cost = self._route_cost(task_id, task_objects[task_id], deadline)
            if route_cost < self._unreachable:
                usable_tasks.append(task_id)
                route_costs[task_id] = route_cost
        tasks = usable_tasks
        if not tasks:
            return schedule

        states = self.env.curr_states
        candidate_edges = []
        candidate_limit = min(64, len(tasks))
        for agent_id in agents:
            if agent_id >= len(states):
                candidate_edges.append([])
                continue
            location = states[agent_id].location

            def choices():
                for task_id in tasks:
                    task = task_objects[task_id]
                    first_goal = task.locations[task.idx_next_loc]
                    distance = self._distance(location, first_goal, deadline)
                    if distance >= self._unreachable:
                        continue
                    yield distance + route_costs[task_id], task_id

            candidate_edges.append(
                heapq.nsmallest(candidate_limit, choices())
            )

        assignment = self._epsilon_auction(
            agents, tasks, candidate_edges, deadline
        )
        for agent_id, task_id in assignment.items():
            schedule[agent_id] = task_id
        return schedule
