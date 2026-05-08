"""路径优化服务（贪心最近邻 + 2-opt）"""
from typing import List, Tuple, Dict
from app.models.poi import POI, DistanceInfo, DistanceMatrix, TransportMode
from app.services.poi_service import TencentMapService
from app.core.exceptions import RouteOptimizationError
import math


class RouteOptimizer:
    def __init__(self, map_service: TencentMapService, max_opt_iterations: int = 100):
        self.map_service = map_service
        self.max_opt_iterations = max_opt_iterations

    async def optimize(
        self,
        pois: List[POI],
        start_poi: POI = None,
        mode: TransportMode = TransportMode.DRIVING,
    ) -> Tuple[List[POI], List[dict]]:
        """优化 POI 访问顺序

        Args:
            pois: 待优化的 POI 列表
            start_poi: 起始 POI（可选，默认第一个）
            mode: 交通方式

        Returns:
            优化后的 POI 列表和路径段信息
        """
        if not pois:
            return [], []
        if len(pois) == 1:
            return pois, []

        try:
            # 构建距离矩阵和 POI→索引映射
            matrix, poi_to_idx = await self._build_matrix(pois, mode)
            # 贪心算法（返回索引序列）
            route_indices = self._greedy(pois, matrix, start_poi, poi_to_idx)
            # 2-opt优化
            if len(route_indices) >= 3:
                route_indices = self._two_opt(route_indices, matrix)
            # 构建段信息
            route = [pois[i] for i in route_indices]
            segments = await self._build_segments(route, mode)
            return route, segments
        except RouteOptimizationError:
            raise
        except Exception as e:
            raise RouteOptimizationError(f"优化失败: {str(e)}")

    async def _build_matrix(
        self, pois: List[POI], mode: TransportMode
    ) -> Tuple[List[List[float]], Dict[str, int]]:
        """构建距离矩阵

        Returns:
            matrix: n×n 距离矩阵，matrix[i][j] 为 pois[i]→pois[j] 距离
            poi_to_idx: POI.id → 矩阵索引映射
        """
        n = len(pois)
        matrix = [[0.0] * n for _ in range(n)]
        poi_to_idx = {poi.id: i for i, poi in enumerate(pois)}
        for i in range(n):
            for j in range(n):
                if i != j:
                    info = await self.map_service.get_distance(pois[i], pois[j], mode)
                    matrix[i][j] = info.distance_meters if info else float('inf')
        return matrix, poi_to_idx

    def _greedy(
        self,
        pois: List[POI],
        matrix: List[List[float]],
        start_poi: POI,
        poi_to_idx: Dict[str, int],
    ) -> List[int]:
        """贪心最近邻算法，返回索引序列"""
        n = len(pois)
        visited = [False] * n
        route = []

        start_idx = poi_to_idx.get(start_poi.id, 0) if start_poi else 0
        route.append(start_idx)
        visited[start_idx] = True

        current = start_idx
        while len(route) < n:
            nearest = min(
                (x for x in range(n) if not visited[x]),
                key=lambda x: matrix[current][x],
            )
            route.append(nearest)
            visited[nearest] = True
            current = nearest
        return route

    def _two_opt(self, route: List[int], matrix: List[List[float]]) -> List[int]:
        """2-opt 局部优化，route 为索引序列"""
        improved = True
        iterations = 0
        best = route[:]
        best_cost = self._calc_cost(best, matrix)

        while improved and iterations < self.max_opt_iterations:
            improved = False
            for i in range(1, len(best) - 2):
                for j in range(i + 1, len(best) - 1):
                    new_route = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                    new_cost = self._calc_cost(new_route, matrix)
                    if new_cost < best_cost:
                        best = new_route
                        best_cost = new_cost
                        improved = True
            iterations += 1
        return best

    @staticmethod
    def _calc_cost(route: List[int], matrix: List[List[float]]) -> float:
        """计算索引路径总距离"""
        return sum(matrix[route[i]][route[i + 1]] for i in range(len(route) - 1))

    async def _build_segments(self, route: List[POI], mode: TransportMode) -> List[dict]:
        """构建路径段信息"""
        segments = []
        for i in range(len(route) - 1):
            info = await self.map_service.get_distance(route[i], route[i + 1], mode)
            if info:
                segments.append({
                    "from": route[i].name,
                    "to": route[i + 1].name,
                    "distance": info.distance_meters,
                    "duration": info.duration_seconds,
                })
        return segments
