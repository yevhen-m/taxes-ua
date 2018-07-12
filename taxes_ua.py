#!/usr/bin/env python
"""
Get UA taxes amounts in no time.

Usage:
    taxes_ua.py STATEMENTS_FILEPATH [--tax-percent=INT]

Options:
    --tax-percent=INT   [default: 5]

Script expects STATEMENTS_FILEPATH to be path to your "statements.xls"
document downloaded from your PB client interface.
"""

from datetime import datetime

import requests

from docopt import docopt
from lxml import html


def get_tax_amount(payments, tax_percent):
    total_amount = sum(
        get_usd_rate(date) * amount for date, amount in payments
    )
    return round(total_amount * float(f'0.0{tax_percent}'), 2)


def get_usd_rate(date):
    NB_API_ENDPOINT_DATE_FMT = '%Y%m%d'
    NB_API_ENDPOINT_URL = (
        'https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange'
        '?valcode=USD&date={date}&json'
    )
    url = NB_API_ENDPOINT_URL.format(
        date=date.strftime(NB_API_ENDPOINT_DATE_FMT)
    )
    response = requests.get(url)
    response.raise_for_status()
    return response.json()[0]['rate']


def parse_statements_document(filepath):
    document = html.parse(filepath)
    table = document.xpath('/html/body/table[2]')[0]
    header, *data, footer = table
    header_text = [cell.text for cell in header]
    EXPECTED_HEADER = [
        '№',
        'Дата проводки',
        'Час проводки',
        'Сума',
        'Валюта',
        'Призначення платежу',
        'ЄДРПОУ',
        'Назва контрагента',
        'Рахунок контрагента',
        'МФО контрагента',
        'Референс',
    ]
    if header_text != EXPECTED_HEADER:
        raise RuntimeError(f'Got unexpected header text {header_text}')

    for row in data:
        if len(row) != len(header) + 1:
            raise RuntimeError('Expected two "sum" cells in each row')

        PAYMENT_SUM_CELL_IDX = 3
        payment_sum = row[PAYMENT_SUM_CELL_IDX].text
        if payment_sum is None:
            continue

        payment_sum = float(payment_sum)
        if payment_sum <= 0:
            raise RuntimeError(
                f'expected to extract positive amount, got {payment_sum}'
            )

        PAYMENT_DATE_CELL_IDX = 1
        payment_date = datetime.strptime(
            row[PAYMENT_DATE_CELL_IDX].text, '%d.%m.%Y'
        )
        yield (payment_date, payment_sum)


def main():
    arguments = docopt(__doc__)
    try:
        tax_percent = int(arguments['--tax-percent'])
    except (ValueError, TypeError):
        raise ValueError('--tax-percent value should be an int') from None

    print(
        'Your tax amount is UAH',
        get_tax_amount(
            parse_statements_document(arguments['STATEMENTS_FILEPATH']),
            tax_percent,
        ),
    )


if __name__ == '__main__':
    main()
