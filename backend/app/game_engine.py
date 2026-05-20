"""
Blackjack game engine — sem OCR, cartas sorteadas pelo servidor.
"""
import random
from typing import Optional, Dict, List
from enum import Enum

SUITS = ['spades', 'hearts', 'diamonds', 'clubs']
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
RANK_VALUES: Dict[str, int] = {
    'A': 11, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
    '8': 8, '9': 9, '10': 10, 'J': 10, 'Q': 10, 'K': 10,
}


class GameStatus(str, Enum):
    WAITING = 'waiting'
    PLAYER_TURN = 'player_turn'
    DEALER_TURN = 'dealer_turn'
    FINISHED = 'finished'


class PlayerStatus(str, Enum):
    WAITING = 'waiting'
    PLAYING = 'playing'
    STOOD = 'stood'
    BUST = 'bust'
    BLACKJACK = 'blackjack'
    WIN = 'win'
    LOSE = 'lose'
    TIE = 'tie'


class Card:
    def __init__(self, rank: str, suit: str, hidden: bool = False):
        self.rank = rank
        self.suit = suit
        self.hidden = hidden

    def to_dict(self) -> dict:
        if self.hidden:
            return {'rank': '?', 'suit': '?', 'hidden': True, 'code': 'back'}
        return {
            'rank': self.rank,
            'suit': self.suit,
            'hidden': False,
            'code': f'{self.rank}_{self.suit}',
        }


class Hand:
    def __init__(self):
        self.cards: List[Card] = []

    def add(self, card: Card):
        self.cards.append(card)

    def value(self) -> int:
        total = sum(RANK_VALUES[c.rank] for c in self.cards if not c.hidden)
        aces = sum(1 for c in self.cards if c.rank == 'A' and not c.hidden)
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def is_bust(self) -> bool:
        return self.value() > 21

    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value() == 21

    def to_list(self) -> list:
        return [c.to_dict() for c in self.cards]


class Player:
    STARTING_BALANCE = 500

    def __init__(self, player_id: str, name: str):
        self.player_id = player_id
        self.name = name
        # Multi-hand support (split creates a second hand)
        self.hands: List[Hand] = [Hand()]
        self.hand_statuses: List[PlayerStatus] = [PlayerStatus.WAITING]
        self.bets: List[int] = [0]
        self.active_hand_idx: int = 0
        self.balance: int = self.STARTING_BALANCE
        self.eliminated: bool = False

    # ── Backward-compat properties ──────────────────────────────────────────

    @property
    def hand(self) -> Hand:
        return self.hands[self.active_hand_idx]

    @hand.setter
    def hand(self, v: Hand):
        self.hands[self.active_hand_idx] = v

    @property
    def status(self) -> PlayerStatus:
        return self.hand_statuses[self.active_hand_idx]

    @status.setter
    def status(self, v: PlayerStatus):
        self.hand_statuses[self.active_hand_idx] = v

    @property
    def bet(self) -> int:
        return self.bets[0]

    @bet.setter
    def bet(self, v: int):
        self.bets = [v]

    # ── Multi-hand helpers ──────────────────────────────────────────────────

    def _advance_hand(self):
        """Move active_hand_idx to the next PLAYING hand (if any)."""
        for i in range(len(self.hand_statuses)):
            if self.hand_statuses[i] == PlayerStatus.PLAYING:
                self.active_hand_idx = i
                return
        # All done — keep idx at last hand for display
        self.active_hand_idx = len(self.hands) - 1

    def is_done(self) -> bool:
        return all(s != PlayerStatus.PLAYING for s in self.hand_statuses)

    def can_split(self) -> bool:
        if len(self.hands) > 1:
            return False  # already split
        h = self.hands[0]
        if len(h.cards) != 2:
            return False
        if self.hand_statuses[0] != PlayerStatus.PLAYING:
            return False
        if h.cards[0].rank != h.cards[1].rank:
            return False
        return self.balance >= self.bets[0]

    def can_double(self) -> bool:
        idx = self.active_hand_idx
        h = self.hands[idx]
        if len(h.cards) != 2:
            return False
        if self.hand_statuses[idx] != PlayerStatus.PLAYING:
            return False
        return self.balance >= self.bets[idx]

    def do_split(self):
        """Split current hand into two. Deducts balance for the second bet."""
        bet = self.bets[0]
        self.balance -= bet
        # Move second card to a new hand
        second_card = self.hands[0].cards.pop()
        hand2 = Hand()
        hand2.add(second_card)
        self.hands.append(hand2)
        self.hand_statuses.append(PlayerStatus.PLAYING)
        self.bets.append(bet)
        self.active_hand_idx = 0

    def to_dict(self) -> dict:
        has_split = len(self.hands) > 1
        return {
            'player_id': self.player_id,
            'name': self.name,
            # Primary hand (always hand 0)
            'hand': self.hands[0].to_list(),
            'hand_value': self.hands[0].value(),
            'status': self.hand_statuses[0].value,
            'bet': self.bets[0],
            # Split hand (if any)
            'split_hand': self.hands[1].to_list() if has_split else None,
            'split_hand_value': self.hands[1].value() if has_split else None,
            'split_status': self.hand_statuses[1].value if has_split else None,
            'split_bet': self.bets[1] if has_split else None,
            'active_hand_idx': self.active_hand_idx,
            # Capabilities (computed server-side)
            'can_split': self.can_split(),
            'can_double': self.can_double(),
            'balance': self.balance,
            'eliminated': self.eliminated,
        }


class Deck:
    DECK_COUNT = 4  # use 4 shuffled decks

    def __init__(self):
        self._cards = [
            Card(r, s)
            for _ in range(self.DECK_COUNT)
            for s in SUITS
            for r in RANKS
        ]
        random.shuffle(self._cards)

    def draw(self, hidden: bool = False) -> Optional[Card]:
        if not self._cards:
            return None
        card = self._cards.pop()
        card.hidden = hidden
        return card

    def remaining(self) -> int:
        return len(self._cards)


class GameEngine:
    def __init__(self):
        self._players: Dict[str, Player] = {}
        self._player_order: List[str] = []  # preserves insertion order
        self._dealer = Player('dealer', 'Dealer')
        self._deck: Optional[Deck] = None
        self.status = GameStatus.WAITING
        self._had_multiple_players: bool = False
        self.game_over_reason: Optional[str] = None   # 'house_wins' | 'player_wins' | None
        self.game_over_winner: Optional[str] = None   # player name when player_wins

    # ── Player management ──────────────────────────────────────────────────

    def add_player(self, player_id: str, name: str) -> bool:
        if player_id in self._players:
            return False
        if self.status not in (GameStatus.WAITING, GameStatus.FINISHED):
            return False
        self._players[player_id] = Player(player_id, name)
        if player_id not in self._player_order:
            self._player_order.append(player_id)
        if len(self._players) >= 2:
            self._had_multiple_players = True
        return True

    def remove_player(self, player_id: str) -> bool:
        if player_id not in self._players:
            return False
        if self.status not in (GameStatus.WAITING, GameStatus.FINISHED):
            return False
        del self._players[player_id]
        self._player_order = [p for p in self._player_order if p != player_id]
        self._check_game_over()
        return True

    def get_player(self, player_id: str) -> Optional[Player]:
        return self._players.get(player_id)

    def _check_game_over(self):
        """Detect end-of-tournament conditions and store the reason."""
        total = len(self._players)
        active = [p for p in self._players.values() if not p.eliminated]
        if total == 0:
            # All players left the table
            self.game_over_reason = 'house_wins'
            self.game_over_winner = None
        elif len(active) == 0:
            # All players are broke
            self.game_over_reason = 'house_wins'
            self.game_over_winner = None
        elif len(active) == 1 and (total > 1 or self._had_multiple_players):
            # Last player standing in a multi-player game
            self.game_over_reason = 'player_wins'
            self.game_over_winner = active[0].name

        # ── Betting ─────────────────────────────────────────────────────────

    def place_bet(self, player_id: str, amount: int) -> bool:
        """Place or replace a bet before the round starts. Returns False if invalid."""
        if self.status not in (GameStatus.WAITING, GameStatus.FINISHED):
            return False
        player = self._players.get(player_id)
        if not player or player.eliminated:
            return False
        if amount < 1 or amount > player.balance:
            return False
        player.bet = amount
        return True

    # ── Round management ───────────────────────────────────────────────────

    def start_round(self) -> bool:
        if not self._players:
            return False
        if self.status not in (GameStatus.WAITING, GameStatus.FINISHED):
            return False
        # All active players must have placed a bet
        active = [p for p in self._players.values() if not p.eliminated]
        if not active or any(p.bet == 0 for p in active):
            return False

        self._deck = Deck()
        self._dealer.hand = Hand()
        self._dealer.status = PlayerStatus.PLAYING

        # Reset hands (non-eliminated only), preserve bets already placed
        for p in self._players.values():
            if p.eliminated:
                continue
            saved_bet = p.bets[0] if p.bets else 0
            p.hands = [Hand()]
            p.hand_statuses = [PlayerStatus.PLAYING]
            p.bets = [saved_bet]
            p.active_hand_idx = 0

        # Deal 2 cards alternating player1…playerN, dealer (skip eliminated)
        for i in range(2):
            for pid in self._player_order:
                p = self._players[pid]
                if p.eliminated:
                    continue
                card = self._deck.draw()
                if card:
                    p.hands[0].add(card)
            # Dealer second card is hidden
            card = self._deck.draw(hidden=(i == 1))
            if card:
                self._dealer.hand.add(card)

        # Check immediate blackjacks
        for p in self._players.values():
            if not p.eliminated and p.hands[0].is_blackjack():
                p.hand_statuses[0] = PlayerStatus.BLACKJACK

        self.status = GameStatus.PLAYER_TURN
        return True

    def player_hit(self, player_id: str) -> Optional[Card]:
        if self.status != GameStatus.PLAYER_TURN:
            return None
        player = self._players.get(player_id)
        if not player or player.status != PlayerStatus.PLAYING:
            return None
        card = self._deck.draw()
        if card:
            player.hand.add(card)
            if player.hand.is_bust():
                player.status = PlayerStatus.BUST
                player._advance_hand()
        return card

    def player_stand(self, player_id: str) -> bool:
        if self.status != GameStatus.PLAYER_TURN:
            return False
        player = self._players.get(player_id)
        if not player or player.status != PlayerStatus.PLAYING:
            return False
        player.status = PlayerStatus.STOOD
        player._advance_hand()
        return True

    def player_split(self, player_id: str) -> bool:
        """Split two equal-rank cards into two hands and deal one extra card each."""
        if self.status != GameStatus.PLAYER_TURN:
            return False
        player = self._players.get(player_id)
        if not player or not player.can_split():
            return False
        player.do_split()
        # Deal one extra card to each of the two new hands
        for i, hand in enumerate(player.hands):
            card = self._deck.draw()
            if card:
                hand.add(card)
            # Auto-blackjack after ace split
            if hand.is_blackjack():
                player.hand_statuses[i] = PlayerStatus.BLACKJACK
        # Start at hand 0; if already done (e.g. blackjack), skip ahead
        player.active_hand_idx = 0
        if player.hand_statuses[0] != PlayerStatus.PLAYING:
            player._advance_hand()
        return True

    def player_double(self, player_id: str) -> Optional[Card]:
        """Double the bet and draw exactly one card. Player can continue acting."""
        if self.status != GameStatus.PLAYER_TURN:
            return None
        player = self._players.get(player_id)
        if not player or not player.can_double():
            return None
        idx = player.active_hand_idx
        extra_bet = player.bets[idx]
        player.balance -= extra_bet
        player.bets[idx] = extra_bet * 2
        card = self._deck.draw()
        if card:
            player.hand.add(card)
            if player.hand.is_bust():
                player.status = PlayerStatus.BUST
                player._advance_hand()
            # No forced stand — player can continue hitting or standing

    def all_players_done(self) -> bool:
        return all(p.is_done() for p in self._players.values())

    def dealer_play(self) -> List[Card]:
        """Reveal hidden card and draw until value >= 17. Returns new cards drawn."""
        if not self.all_players_done():
            return []
        self.status = GameStatus.DEALER_TURN

        # Reveal hidden card
        for card in self._dealer.hand.cards:
            card.hidden = False

        drawn: List[Card] = []
        while self._dealer.hand.value() < 17:
            card = self._deck.draw()
            if card:
                self._dealer.hand.add(card)
                drawn.append(card)

        if self._dealer.hand.is_bust():
            self._dealer.status = PlayerStatus.BUST
        else:
            self._dealer.status = PlayerStatus.STOOD
        return drawn

    def calculate_results(self):
        dealer_value = self._dealer.hand.value()
        dealer_bust = self._dealer.status == PlayerStatus.BUST

        for p in self._players.values():
            # Resolve every hand (1 normally, 2 after split)
            for i in range(len(p.hands)):
                hs  = p.hand_statuses[i]
                h   = p.hands[i]
                bet = p.bets[i]

                if hs == PlayerStatus.BUST:
                    result = PlayerStatus.LOSE
                elif hs == PlayerStatus.BLACKJACK:
                    result = PlayerStatus.TIE if self._dealer.hand.is_blackjack() else PlayerStatus.WIN
                elif dealer_bust:
                    result = PlayerStatus.WIN
                else:
                    hv = h.value()
                    if hv > dealer_value:
                        result = PlayerStatus.WIN
                    elif hv < dealer_value:
                        result = PlayerStatus.LOSE
                    else:
                        result = PlayerStatus.TIE

                p.hand_statuses[i] = result
                if result == PlayerStatus.WIN:
                    p.balance += bet
                elif result == PlayerStatus.LOSE:
                    p.balance -= bet
                # TIE → no change

            if p.balance <= 0:
                p.balance = 0
                p.eliminated = True

        self._check_game_over()
        self.status = GameStatus.FINISHED

    def reset(self):
        """Reset to WAITING while keeping players registered (and their balances)."""
        self._dealer.hand = Hand()
        self._dealer.status = PlayerStatus.WAITING
        for p in self._players.values():
            p.hands = [Hand()]
            p.hand_statuses = [PlayerStatus.WAITING]
            p.bets = [0]         # clear bet so player must bet again
            p.active_hand_idx = 0
        self._deck = None
        self.status = GameStatus.WAITING
        self.game_over_reason = None
        self.game_over_winner = None

    def new_game(self):
        """Full reset: remove all players and start fresh."""
        self._players.clear()
        self._player_order.clear()
        self._dealer.hand = Hand()
        self._dealer.status = PlayerStatus.WAITING
        self._deck = None
        self.status = GameStatus.WAITING
        self._had_multiple_players = False
        self.game_over_reason = None
        self.game_over_winner = None

    # ── Serialization ──────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            'status': self.status.value,
            'players': [self._players[pid].to_dict() for pid in self._player_order],
            'dealer': self._dealer.to_dict(),
            'deck_remaining': self._deck.remaining() if self._deck else 52,
            'game_over_reason': self.game_over_reason,
            'game_over_winner': self.game_over_winner,
        }
