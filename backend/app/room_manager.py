import re
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.game_engine import GameEngine

DEFAULT_ROOM_ID = 'mesa-principal'


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', value.strip().lower())
    slug = slug.strip('-')
    return slug or 'mesa'


@dataclass
class RoomState:
    room_id: str
    name: str
    table_terminal_id: str
    game: GameEngine = field(default_factory=GameEngine)

    def to_dict(self) -> dict:
        data = self.game.to_dict()
        players = data.get('players', [])
        active_players = [player for player in players if not player.get('eliminated')]
        data.update(
            {
                'room_id': self.room_id,
                'room_name': self.name,
                'table_terminal_id': self.table_terminal_id,
                'player_count': len(players),
                'active_player_count': len(active_players),
            }
        )
        return data

    def summary(self) -> dict:
        state = self.to_dict()
        return {
            'room_id': self.room_id,
            'name': self.name,
            'table_terminal_id': self.table_terminal_id,
            'status': state['status'],
            'player_count': state['player_count'],
            'active_player_count': state['active_player_count'],
            'deck_remaining': state['deck_remaining'],
            'game_over_reason': state['game_over_reason'],
            'game_over_winner': state['game_over_winner'],
        }


class RoomRegistry:
    def __init__(self):
        self._rooms: Dict[str, RoomState] = {}

    def all_rooms(self) -> list[RoomState]:
        return list(self._rooms.values())

    def list_rooms(self) -> list[dict]:
        return [room.summary() for room in self._rooms.values()]

    def get_room(self, room_id: str) -> Optional[RoomState]:
        return self._rooms.get(room_id)

    def delete_room(self, room_id: str) -> Optional[RoomState]:
        return self._rooms.pop(room_id, None)

    def create_room(self, name: str, room_id: Optional[str] = None) -> RoomState:
        base_room_id = _slugify(room_id or name)
        candidate = base_room_id
        suffix = 2
        while candidate in self._rooms:
            candidate = f'{base_room_id}-{suffix}'
            suffix += 1

        room = RoomState(
            room_id=candidate,
            name=name.strip() or 'Mesa',
            table_terminal_id=f'table-{candidate}',
        )
        self._rooms[candidate] = room
        return room

    def get_or_create_default(self) -> RoomState:
        room = self.get_room(DEFAULT_ROOM_ID)
        if room is None:
            room = RoomState(
                room_id=DEFAULT_ROOM_ID,
                name='Mesa Principal',
                table_terminal_id=f'table-{DEFAULT_ROOM_ID}',
            )
            self._rooms[DEFAULT_ROOM_ID] = room
        return room