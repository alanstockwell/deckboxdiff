#!/usr/bin/env python3

from decimal import Decimal, InvalidOperation
from collections import defaultdict

from argparse import ArgumentParser
from copy import deepcopy

import pandas as pd


CONDITION_PRICE_MULTIPLIERS = {
    '': Decimal('1.00'),  # Assume Mint/Near Mint
    'Mint': Decimal('1.00'),
    'Near Mint': Decimal('1.00'),
    'Good (Lightly Played)': Decimal('0.85'),
    'Played': Decimal('0.70'),
    'Heavily Played': Decimal('0.50'),
    'Poor': Decimal('0.25'),
}


class Card(object):
    _price = None
    _my_price = None

    def __init__(self, edition, card_number, name, card_type, cost, rarity, count, condition, language,
                 foil, signed, artist_proof, altered_art, misprint, promo, textless, image_url):
        self.edition = edition
        self.card_number = card_number
        self.name = name
        self.card_type = card_type
        self.cost = cost
        self.rarity = rarity
        self.count = count
        self.condition = condition
        self.language = language
        self.foil = foil
        self.signed = signed
        self.artist_proof = artist_proof
        self.altered_art = altered_art
        self.misprint = misprint
        self.promo = promo
        self.textless = textless
        self.image_url = image_url

    def __str__(self):
        return '{} x {}'.format(
            self.count,
            self.description,
        )

    def __repr__(self):
        return '<{}>'.format(self)

    @staticmethod
    def from_deckbox_row(row):
        card = Card(
            edition=row.loc['Edition'],
            card_number=row.loc['Card Number'],
            name=row.loc['Name'],
            card_type=row.loc['Type'],
            cost=row.loc['Cost'],
            rarity=row.loc['Rarity'],
            count=row.loc['Count'],
            condition='' if pd.isna(row.loc['Condition']) else row.loc['Condition'],
            language=row.loc['Language'],
            foil='' if pd.isna(row.loc['Foil']) else row.loc['Foil'],
            signed='' if pd.isna(row.loc['Signed']) else row.loc['Signed'],
            artist_proof='' if pd.isna(row.loc['Artist Proof']) else row.loc['Artist Proof'],
            altered_art='' if pd.isna(row.loc['Altered Art']) else row.loc['Altered Art'],
            misprint='' if pd.isna(row.loc['Misprint']) else row.loc['Misprint'],
            promo='' if pd.isna(row.loc['Promo']) else row.loc['Promo'],
            textless='' if pd.isna(row.loc['Textless']) else row.loc['Textless'],
            image_url=row.loc['Image URL'],
        )

        try:
            card.price = row.loc['Price'].lstrip('$')
        except (KeyError, InvalidOperation):
            pass

        try:
            card.my_price = row.loc['My Price'].lstrip('$')
        except (KeyError, InvalidOperation):
            pass

        return card

    @property
    def description(self):
        features = self.features

        return '{} ({}, #{:03d}) | {}{}'.format(
            self.name,
            self.edition,
            self.card_number,
            self.condition,
            '' if len(features) == 0 else ', {}'.format(', '.join((_.title() for _ in features))),
        )

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        self._price = None if value is None else Decimal(value)

    @property
    def condition_adjusted_price(self):
        return None if self._price is None else self._price * CONDITION_PRICE_MULTIPLIERS[self.condition]

    @property
    def my_price(self):
        return self._my_price

    @my_price.setter
    def my_price(self, value):
        self._my_price = None if value is None else Decimal(value)

    @property
    def total_price(self):
        return None if self._price is None else self.price * self.count

    @property
    def total_condition_adjusted_price(self):
        return None if self._price is None else self.condition_adjusted_price * self.count

    @property
    def total_my_price(self):
        return None if self.my_price is None else self.count * self.my_price

    @property
    def features(self):
        return list(filter(lambda x: not x == '', (
            self.foil,
            self.signed,
            self.artist_proof,
            self.altered_art,
            self.misprint,
            self.promo,
            self.textless,
        )))

    @property
    def identity(self):
        return self.type + (
            self.condition,
        )

    @property
    def type(self):
        return (
            self.edition,
            self.card_number,
            self.name,
            self.language,
            self.foil,
            self.signed,
            self.artist_proof,
            self.altered_art,
            self.misprint,
            self.promo,
            self.textless,
            self.image_file_name,  # Un-sets sometimes have different images for the same edition/card_number
        )

    @property
    def image_file_name(self):
        return None if self.image_url is None else self.image_url.split('/')[-1]

    def clone(self, count=None):
        new_clone = deepcopy(self)

        if count is not None:
            new_clone.count = count

        return new_clone


class CardSet(object):

    def __init__(self):
        self.cards = {}
        self.types = defaultdict(list)

    def __add__(self, other_card_set):
        new_set = CardSet()

        for card in self.cards.values():
            new_set.add_card(card)

        for card in other_card_set.cards.values():
            new_set.add_card(card)

        return new_set

    def __contains__(self, card):
        return self.contains(card)

    def __eq__(self, other_card_set):
        for self_card in self.cards.values():
            if self_card not in other_card_set:
                return False

        for other_card in other_card_set.cards.values():
            self_card = self.match(other_card)

            if self_card is None or not other_card.count == self_card.count:
                return False

        return True

    def __len__(self):
        return sum((_.count for _ in self.cards.values()))

    @property
    def total_price(self):
        return sum((_.total_price for _ in self.cards.values() if _.total_price is not None))

    @property
    def total_condition_adjusted_price(self):
        return sum((_.total_condition_adjusted_price for _ in self.cards.values() if _.total_price is not None))

    @property
    def total_my_price(self):
        return sum((_.total_my_price for _ in self.cards.values() if _.total_my_price is not None))

    def add_card(self, card):
        try:
            self.cards[card.identity].count += card.count
        except KeyError:
            self.cards[card.identity] = card

        self.types[card.type].append(card)

    def contains(self, other_card):
        self_card = self.match(other_card)

        return self_card is not None and self_card.count == other_card.count

    def contains_type(self, card):
        return card.type in self.types

    def match(self, card):
        try:
            return self.cards[card.identity]
        except KeyError:
            return None

    def iter_diff(self, other_card_set):
        for card in self.cards.values():
            other_card = other_card_set.match(card)

            if other_card is None:
                yield card.clone(count=0 - card.count)
            elif not other_card.count == card.count:
                yield card.clone(other_card.count - card.count)

        for other_card in other_card_set.cards.values():
            self_match = self.match(other_card)

            if self_match is None:
                yield other_card.clone()

    def diff_set(self, other_card_set):
        differences = list(self.iter_diff(other_card_set))

        differences.sort(key=lambda x: x.identity)

        new_set = CardSet()

        for card in differences:
            new_set.add_card(card)

        return new_set

    def diff_price(self, other_card_set):
        return self.diff_set(other_card_set).total_applied_price(other_card_set)

    def apply_card_pricing(self, other_card, condition_adjusted=False):
        try:
            result = other_card.count * self.types[other_card.type][0].price

            if condition_adjusted:
                return result * CONDITION_PRICE_MULTIPLIERS[other_card.condition]
            else:
                return result
        except (KeyError, IndexError):
            raise ValueError(
                'Cannot adjust price for: {}'.format(
                    other_card.description,
                ),
            )

    def total_applied_price(self, other_card_set, condition_adjusted=False):
        return sum((
            other_card_set.apply_card_pricing(_, condition_adjusted=condition_adjusted)
            for _ in
            self.cards.values()
        ))


class DeckboxExport(object):
    FILE_TYPE_CSV = 'csv'
    FILE_TYPE_XLSX = 'xlsx'

    EXCEL_ENCODING_CLEANUPS = (
        ('Ã©', 'é'),
    )

    DATA_TYPES = {
        'Price': str,
        'My Price': str,
        'Cost': str,
    }

    def __init__(self, file_path):
        self.file_path = file_path
        self.file_type = self.file_path.lower().split('.')[-1]

        if self.file_type == DeckboxExport.FILE_TYPE_CSV:
            self._data = pd.read_csv(self.file_path, dtype=self.DATA_TYPES)
        elif self.file_type == DeckboxExport.FILE_TYPE_XLSX:
            self._data = pd.read_excel(self.file_path, dtype=self.DATA_TYPES, engine='openpyxl')
        else:
            raise TypeError('Only CSV and XLSX files are supported')

        self.card_set = CardSet()

        for row in (self._data.loc[_].copy() for _ in self._data.index):
            if self.file_type == DeckboxExport.FILE_TYPE_XLSX:
                for replace_from, replace_to in DeckboxExport.EXCEL_ENCODING_CLEANUPS:
                    row.loc['Name'] = row.loc['Name'].replace(replace_from, replace_to)

            self.card_set.add_card(Card.from_deckbox_row(row))


if __name__ == '__main__':
    parser = ArgumentParser('Calculate the difference between two deckbox export files')

    parser.add_argument(
        'earlier_file',
        help='The earlier file used for reference',
    )
    parser.add_argument(
        'later_file',
        help='The later file to calculate the changes in relative to the earlier file '
             '(Also used to calculate the adjusted price of the earlier set)',
    )
    parser.add_argument('-p', '--show-price', action='store_true', help='Show price difference between sets')

    args = parser.parse_args()

    earlier_set = DeckboxExport(args.earlier_file).card_set
    later_set = DeckboxExport(args.later_file).card_set
    diff_set = earlier_set.diff_set(later_set)

    for difference in diff_set.cards.values():
        print(difference)

    try:
        if args.show_price:
            print(
                '\n'
                'Earlier set price:\n'
                '  ${:,.2f} M/NM\n'
                '  ${:,.2f} M/NM (updated)\n'
                '  ${:,.2f} (updated and condition adjusted)'.format(
                    earlier_set.total_price,
                    earlier_set.total_applied_price(later_set),
                    earlier_set.total_applied_price(later_set, condition_adjusted=True),
                ))
            print(
                'Later set price:\n'
                '  ${:,.2f} M/NM\n'
                '  ${:,.2f} (condition adjusted)'.format(
                    later_set.total_price,
                    later_set.total_condition_adjusted_price,
                ))
            print(
                'Adjusted price delta:\n'
                '  ${:,.2f} M/NM\n'
                '  ${:,.2f} (condition adjusted)'.format(
                    diff_set.total_applied_price(later_set),
                    diff_set.total_applied_price(later_set, condition_adjusted=True),
                ))
    except ValueError as e:
        print('\nCannot show pricing due to error below:')
        print('  {}'.format(e))
