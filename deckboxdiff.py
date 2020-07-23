#!/usr/bin/env python3

from argparse import ArgumentParser

import pandas as pd


class CardInstance(object):

    def __init__(self, edition, card_number, name, count):
        self.edition = edition
        self.card_number = card_number
        self.name = name
        self.count = count

    def __str__(self):
        return '{} x {} - {}, Card #{}'.format(
            self.count,
            self.name,
            self.edition,
            self.card_number,
        )

    @staticmethod
    def from_deckbox_row(row):
        return CardInstance(
            edition=row.loc['Edition'],
            card_number=row.loc['Card Number'],
            name=row.loc['Name'],
            count=row.loc['Count'],
        )

    @property
    def set_key(self):
        return self.edition, self.card_number, self.name

    def clone(self, count=None):
        return CardInstance(
            edition=self.edition,
            card_number=self.card_number,
            name=self.name,
            count=self.count if count is None else count,
        )


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

    parser.add_argument('file_one', help='The reference file')
    parser.add_argument('file_two', help='The file which is different to the reference file')

    args = parser.parse_args()

    reference_set = DeckboxExport(args.file_one).card_set
    difference_set = DeckboxExport(args.file_two).card_set

    for difference in reference_set.diff(difference_set):
        print(difference)
