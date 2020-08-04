from django.db import models

class AbstractModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract=True


class Products(AbstractModel):
    name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=5, decimal_places=2)

    def dispense(self):
        self.quantity -= 1
        self.save()


class Machine(AbstractModel):
    STATE_READY = 1
    STATE_CURRENCY_INSERTED = 2
    STATE_DISPENSING = 3
    STATE_OUT_OF_STOCK = 4
    STATE_MAINTENANCE = 10

    STATE_CHOICES = (
        (STATE_READY, 'Ready'),
        (STATE_CURRENCY_INSERTED, 'Currency Inserted'),
        (STATE_DISPENSING, 'Dispensing Item'),
        (STATE_OUT_OF_STOCK, 'Out of Stock'),
        (STATE_MAINTENANCE, 'Under Maintenance')
    )

    state = models.IntegerField(choices=STATE_CHOICES, default=STATE_READY)
    message = models.CharField(max_length=100, null=True, blank=True)
    last_transaction = models.ForeignKey('MachineTransaction', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=6, decimal_places=2, default=0)

class MachineTransaction(AbstractModel):
    ACTION_INSERT_DENOMINATION = 1
    ACTION_USER_CANCEL = 2
    ACTION_SELECT_ITEM = 3
    ACTION_REFUND = 4
    ACTION_CANCELLED_BY_MACHINE = 10
    ACTION_MAINTENANCE_ADD_PRODUCT = 11
    ACTION_MAINTENANCE_WITHRAW_CURRENCY = 12

    ACTION_CUSTOMER_CHOICES = (
        (ACTION_INSERT_DENOMINATION, 'currency inserted'),
        (ACTION_USER_CANCEL, 'cancelled by user'),
        (ACTION_SELECT_ITEM, 'item selected by user'),
        (ACTION_REFUND, 'refund amount'),
        (ACTION_CANCELLED_BY_MACHINE, 'called by machine'),
        (ACTION_MAINTENANCE_ADD_PRODUCT, 'Admin add product'),
        (ACTION_MAINTENANCE_WITHRAW_CURRENCY, 'Admin currency withdraw')
    )

    DENOMINATOION_10 = 10
    DENOMINATOION_20 = 20
    DENOMINATOION_50 = 50
    DENOMINATOION_100 = 100

    DENOMINATOION_CHOICES_DICT = {
        DENOMINATOION_10: '10',
        DENOMINATOION_20: '20',
        DENOMINATOION_50: '50',
        DENOMINATOION_100: '100'
    }

    action = models.IntegerField(choices=ACTION_CUSTOMER_CHOICES)
    activity_log = models.CharField(max_length=100, null=True, blank=True)
    amount = models.DecimalField(max_digits=5, decimal_places=2)
    total_transaction_amount = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    denomination = models.IntegerField(choices=DENOMINATOION_CHOICES_DICT.items(), null=True, blank=True)
    product = models.ForeignKey(Products, on_delete=models.PROTECT, null=True, blank=True)
