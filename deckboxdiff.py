#!/usr/bin/env python3

from decimal import Decimal, InvalidOperation

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


class CardInstance(object):
    _price = None
    _my_price = None

    def __init__(self, edition, card_number, name, card_type, rarity, count, condition, language,
                 foil, signed, artist_proof, altered_art, misprint, promo, textless, image_url):
        self.edition = edition
        self.card_number = card_number
        self.name = name
        self.card_type = card_type
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

    @staticmethod
    def from_deckbox_row(row):
        card_instance = CardInstance(
            edition=row.loc['Edition'],
            card_number=row.loc['Card Number'],
            name=row.loc['Name'],
            card_type=row.loc['Type'],
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
            card_instance.price = row.loc['Price'].lstrip('$')
        except (KeyError, InvalidOperation):
            pass

        try:
            card_instance.my_price = row.loc['My Price'].lstrip('$')
        except (KeyError, InvalidOperation):
            pass

        return card_instance

    @property
    def description(self):
        features = self.features

        return '{} - {}, Card #{} - {}{}'.format(
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
    def set_key(self):
        return self.price_key + (
            self.condition,
        )

    @property
    def price_key(self):
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
        self.prices = {}

    def __add__(self, other):
        new_set = CardSet()

        for card_instance in self.cards.values():
            new_set.add_card(card_instance)

        for card_instance in other.cards.values():
            new_set.add_card(card_instance)

        return new_set

    def __eq__(self, other):
        for card_instance in self.cards.values():
            other_match = other.match(card_instance)

            if other_match is None or not card_instance.count == other_match.count:
                return False

        for card_instance in other.cards.values():
            self_match = self.match(card_instance)

            if self_match is None or not card_instance.count == self_match.count:
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

    def add_card(self, card_instance):
        try:
            self.cards[card_instance.set_key].count += card_instance.count
        except KeyError:
            self.cards[card_instance.set_key] = card_instance

        try:
            existing_price = self.prices[card_instance.price_key]

            if not existing_price == card_instance.price:
                raise ValueError('Price does not match for {}: {} vs {}'.format(
                    card_instance,
                    existing_price,
                    card_instance.price,
                ))
        except KeyError:
            self.prices[card_instance.price_key] = card_instance.price

    def match(self, card_instance):
        try:
            return self.cards[card_instance.set_key]
        except KeyError:
            return None

    def iter_diff(self, other):
        for card_instance in self.cards.values():
            other_match = other.match(card_instance)

            if other_match is None:
                yield card_instance.clone(count=0 - card_instance.count)
            elif not other_match.count == card_instance.count:
                yield card_instance.clone(other_match.count - card_instance.count)

        for other_card_instance in other.cards.values():
            self_match = self.match(other_card_instance)

            if self_match is None:
                yield other_card_instance.clone()

    def diff_set(self, other):
        differences = list(self.iter_diff(other))

        differences.sort(key=lambda x: x.set_key)

        new_set = CardSet()

        for card_instance in differences:
            new_set.add_card(card_instance)

        return new_set

    def diff_price(self, other):
        return self.diff_set(other).total_adjusted_price(other)

    def adjust_price(self, other_card_instance):
        try:
            return other_card_instance.count * self.prices[other_card_instance.price_key]
        except KeyError:
            raise ValueError(
                'Cannot adjust price for: {}'.format(
                    other_card_instance.description,
                ),
            )

    def total_adjusted_price(self, other):
        return sum((other.adjust_price(_) for _ in self.cards.values()))


class DeckboxExport(object):
    FILE_TYPE_CSV = 'csv'
    FILE_TYPE_XLSX = 'xlsx'

    EXCEL_ENCODING_CLEANUPS = (
        ('Ã©', 'é'),
    )

    DATA_TYPES = {
        'Price': str,
        'My Price': str,
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

            self.card_set.add_card(CardInstance.from_deckbox_row(row))


if __name__ == '__main__':
    parser = ArgumentParser('Calculate the difference between two deckbox export files')

    parser.add_argument('reference_file', help='The reference file')
    parser.add_argument('difference_file', help='The file to calculate the deltas of relative to the reference file')
    parser.add_argument('-p', '--show-price', action='store_true', help='Show price difference between sets')

    args = parser.parse_args()

    reference_set = DeckboxExport(args.reference_file).card_set
    difference_set = DeckboxExport(args.difference_file).card_set

    for difference in reference_set.diff_set(difference_set).cards.values():
        print(difference)

    try:
        if args.show_price:
            print('\nReference set price: ${:,.2f} (${:,.2f} adjusted)'.format(
                reference_set.total_price,
                reference_set.total_adjusted_price(difference_set),
            ))
            print('Difference set price: ${:,.2f}'.format(
                difference_set.total_price,
            ))
            print('Difference set condition adjusted price: ${:,.2f}'.format(
                difference_set.total_condition_adjusted_price,
            ))
            print('Adjusted price delta: ${:,.2f}'.format(
                reference_set.diff_price(difference_set),
            ))
    except ValueError as e:
        print('\nCannot show pricing due to error below:')
        print('  {}'.format(e))
