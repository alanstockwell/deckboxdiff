#!/usr/bin/env python3

from argparse import ArgumentParser
from copy import deepcopy

import pandas as pd


class CardInstance(object):

    def __init__(self, edition, card_number, name, card_type, rarity, count, condition, language,
                 foil, signed, artist_proof, altered_art, misprint, promo, textless):
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

    def __str__(self):
        features = self.features

        return '{} x {} - {}, Card #{} - {}{}'.format(
            self.count,
            self.name,
            self.edition,
            self.card_number,
            self.condition,
            '' if len(features) == 0 else ', {}'.format(', '.join((_.title() for _ in features))),
        )

    @staticmethod
    def from_deckbox_row(row):
        return CardInstance(
            edition=row.loc['Edition'],
            card_number=row.loc['Card Number'],
            name=row.loc['Name'],
            card_type=row.loc['Type'],
            rarity=row.loc['Rarity'],
            count=row.loc['Count'],
            condition=row.loc['Condition'],
            language=row.loc['Language'],
            foil='' if pd.isna(row.loc['Foil']) else row.loc['Foil'],
            signed='' if pd.isna(row.loc['Signed']) else row.loc['Signed'],
            artist_proof='' if pd.isna(row.loc['Artist Proof']) else row.loc['Artist Proof'],
            altered_art='' if pd.isna(row.loc['Altered Art']) else row.loc['Altered Art'],
            misprint='' if pd.isna(row.loc['Misprint']) else row.loc['Misprint'],
            promo='' if pd.isna(row.loc['Promo']) else row.loc['Promo'],
            textless='' if pd.isna(row.loc['Textless']) else row.loc['Textless'],
        )

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
        return (
            self.edition,
            self.card_number,
            self.name,
            self.condition,
            self.language,
            self.foil,
            self.signed,
            self.artist_proof,
            self.altered_art,
            self.misprint,
            self.promo,
            self.textless,
        )

    def clone(self, count=None):
        new_clone = deepcopy(self)

        if count is not None:
            new_clone.count = count

        return new_clone


class CardSet(object):

    def __init__(self):
        self.cards = {}

    def add_card(self, card_instance):
        try:
            self.cards[card_instance.set_key].count += card_instance.count
        except KeyError:
            self.cards[card_instance.set_key] = card_instance

    def match(self, card_instance):
        try:
            return self.cards[card_instance.set_key]
        except KeyError:
            return None

    def diff(self, other):
        differences = []

        for card_instance in self.cards.values():
            other_match = other.match(card_instance)

            if other_match is None:
                differences.append(card_instance.clone(count=0 - card_instance.count))
            elif not other_match.count == card_instance.count:
                differences.append(card_instance.clone(other_match.count - card_instance.count))

        for other_card_instance in other.cards.values():
            self_match = self.match(other_card_instance)

            if self_match is None:
                differences.append(other_card_instance.clone())

        differences.sort(key=lambda x: x.set_key)

        return differences


class DeckboxExport(object):
    FILE_TYPE_CSV = 'csv'
    FILE_TYPE_XLSX = 'xlsx'

    def __init__(self, file_path):
        self.file_path = file_path
        self.file_type = self.file_path.lower().split('.')[-1]

        if self.file_type == DeckboxExport.FILE_TYPE_CSV:
            self._data = pd.read_csv(self.file_path)
        elif self.file_type == DeckboxExport.FILE_TYPE_XLSX:
            self._data = pd.read_excel(self.file_path)
        else:
            raise TypeError('Only CSV and XLSX files are supported')

        self.card_set = CardSet()

        for row in (self._data.loc[_] for _ in self._data.index):
            self.card_set.add_card(CardInstance.from_deckbox_row(row))


if __name__ == '__main__':
    parser = ArgumentParser('Calculate the difference between two deckbox export files')

    parser.add_argument('reference_file', help='The reference file')
    parser.add_argument('difference_file', help='The file to calculate the deltas of relative to the reference file')

    args = parser.parse_args()

    reference_set = DeckboxExport(args.reference_file).card_set
    difference_set = DeckboxExport(args.difference_file).card_set

    for difference in reference_set.diff(difference_set):
        print(difference)
