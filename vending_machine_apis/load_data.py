import inspect
import os
import sys

import django

base_dir = os.path.dirname(
    os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
print(base_dir)
# base_dir = os.path.dirname()
sys.path.append(base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from machine.models import *

products = [
    {'name': 'Lays', 'price': 20, 'quantity': 10},
    {'name': 'Uncle Chips', 'price': 25, 'quantity': 10},
    {'name': 'Kurkure', 'price': 20, 'quantity': 10},
    {'name': 'Britania Cake', 'price': 50, 'quantity': 10},
    {'name': 'Bisleri', 'price': 20, 'quantity': 10},
    {'name': 'Coke', 'price': 40, 'quantity': 10},
    {'name': 'Pepsi', 'price': 40, 'quantity': 10},
    {'name': 'Mars', 'price': 30, 'quantity': 10},
    {'name': 'KitKat', 'price': 25, 'quantity': 10},
]

for each_product in products:
    Products.objects.create(**each_product)

Machine.objects.create(state=Machine.STATE_READY, amount=100, message="Ready !!!")