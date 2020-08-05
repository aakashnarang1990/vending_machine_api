from rest_framework import serializers
from rest_framework.exceptions import NotAcceptable, ValidationError
from machine.models import Machine, MachineTransaction, Products
from decimal import Decimal


class ProductSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = Products
        fields = ['id', 'name', 'price', 'quantity']


    def validate_quantity(self, qty):
        if qty < 1:
            raise ValidationError('Please select a valid quantity for product')
        return qty

    def update(self, instance, validated_data):
        product_obj = super(ProductSerializer, self).update(instance, validated_data)
        if Machine.objects.last().state == Machine.STATE_OUT_OF_STOCK and product_obj.quantity > 0:
            Machine.objects.all().update(state=Machine.STATE_READY)
        return product_obj


class TransactionSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, write_only=True)
    quantity = serializers.IntegerField(required=False, write_only=True)
    action_performed = serializers.CharField(source = 'get_action_display', read_only=True)
    denomination = serializers.IntegerField(write_only=True, required=False)
    action = serializers.IntegerField(write_only=True)
    # product = serializers.ModelField(model_field='products_id', read_only=True)

    class Meta:
        model = MachineTransaction
        fields = ('action', 'denomination', 'product', 'activity_log', 'amount', 'quantity', 'action_performed')
        # read_only_fields = ('activity_log', 'action_performed')

    def validate_product(self, product):
        if self.initial_data.get('action') == MachineTransaction.ACTION_SELECT_ITEM:
            if product.quantity == 0:
                raise ValidationError("Item is out of stock, Please select any other item")
            if product.price > self.context.get('machine').last_transaction.total_transaction_amount:
                raise ValidationError(
                    "you are short of Rs {}. Please insert amount to continue or choose any other item".format(
                        product.price - self.context.get('machine').last_transaction.total_transaction_amount
                    ))
            return product
        if self.initial_data.get('action') == MachineTransaction.ACTION_MAINTENANCE_ADD_PRODUCT:
            return product

    def validate_quantity(self, qty):
        if self.initial_data.get('action') == MachineTransaction.ACTION_MAINTENANCE_ADD_PRODUCT:
            if not qty:
                raise ValidationError("Please enter quantity of the product to add")
            if qty < 1:
                raise ValidationError('Please select a valid quantity for product')
            return qty

    def validate_denomination(self, denomination):
        if self.initial_data.get('action') == MachineTransaction.ACTION_INSERT_DENOMINATION:
            if not denomination:
                raise ValidationError("please insert money before proceeding")
            if self.initial_data.get('denomination') not in MachineTransaction.DENOMINATOION_CHOICES_DICT.keys():
                raise ValidationError("unknown currency inserted")
            return denomination

    def validate(self, attrs):
        self.refund_serialiser = None

        # handling if currency is inserted
        if attrs.get('action') == MachineTransaction.ACTION_INSERT_DENOMINATION:
            attrs['amount'] = attrs.get('denomination')
            attrs['total_transaction_amount'] = attrs.get('denomination')
            if self.context.get('machine').state == Machine.STATE_CURRENCY_INSERTED:
                attrs['total_transaction_amount'] += self.context.get('machine').last_transaction.total_transaction_amount
            attrs["activity_log"] = "Rs {} inserted, Please Select Item".format(attrs['amount'])

        # handling when item is selected
        elif attrs.get('action') == MachineTransaction.ACTION_SELECT_ITEM:
            attrs['amount'] = 0
            attrs['total_transaction_amount'] = 0
            attrs["activity_log"] = "Please collect {}. ".format(attrs['product'].name)
            if attrs.get('product').price < self.context.get('machine').last_transaction.total_transaction_amount:
                refund_amount = self.context.get('machine').last_transaction.total_transaction_amount \
                                - attrs.get('product').price
                self.refund_serialiser = TransactionSerializer(data={
                    "action": MachineTransaction.ACTION_REFUND,
                    "activity_log": attrs['activity_log'] + "Collect balance Rs {}".format(refund_amount),
                    "amount": refund_amount,
                })
                self.refund_serialiser.is_valid(raise_exception=True)

        # Handling when user cancelled the transaction
        elif attrs.get('action') == MachineTransaction.ACTION_USER_CANCEL:
            if self.context.get('machine').state == Machine.STATE_CURRENCY_INSERTED:
                refund_amount = self.context.get('machine').last_transaction.total_transaction_amount
                attrs["activity_log"] = "Transaction Cancelled, Collect Rs {}".format(refund_amount)
                attrs["amount"] = refund_amount
                attrs["total_transaction_amount"] = 0

        # Handling for Refund Payment
        elif attrs.get('action') == MachineTransaction.ACTION_REFUND:
            pass

        # Handling for payment withdraw
        elif attrs.get('action') == MachineTransaction.ACTION_MAINTENANCE_WITHRAW_CURRENCY:
            attrs["activity_log"] = "Rs {} withdrawn by admin".format(attrs['amount'])
            # attrs["amount"] = refund_amount
            attrs["total_transaction_amount"] = 0

        # Handling for product add
        elif attrs.get('action') == MachineTransaction.ACTION_MAINTENANCE_ADD_PRODUCT:
            attrs['amount'] = 0
            attrs['total_transaction_amount'] = 0
            attrs["activity_log"] = "added {} units of {}. ".format(attrs['quantity'], attrs['product'].name)
            attrs['quantity'] += attrs['product'].quantity
            self.product_serializer = ProductSerializer(data = {"quantity": attrs.pop('quantity')},
                                                         instance = attrs['product']
                                                         )
            self.product_serializer.is_valid(raise_exception=True)
        return attrs


    def create(self, validated_data):
        transaction_obj = super(TransactionSerializer, self).create(validated_data=validated_data)
        if transaction_obj.action == MachineTransaction.ACTION_SELECT_ITEM:
            transaction_obj.product.dispense()
        elif transaction_obj.action == MachineTransaction.ACTION_MAINTENANCE_ADD_PRODUCT:
            self.product_serializer.save()
        if self.refund_serialiser is not None:
            return self.refund_serialiser.save()
        return transaction_obj


class MachineSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display', read_only=True)
    amount = serializers.SerializerMethodField()
    total_amount = serializers.DecimalField(max_digits=6, decimal_places=2, source='amount')
    # product = serializers.IntegerField(write_only=True)
    # denomination = serializers.IntegerField(write_only=True)

    class Meta:
        fields = ('state', 'message', 'amount', 'total_amount')
        model = Machine

    def get_amount(self, obj):
        if obj.state == Machine.STATE_CURRENCY_INSERTED:
            return obj.last_transaction.total_transaction_amount
        else:
            return Decimal(0)


class AddCurrencySerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display', read_only=True)
    amount = serializers.SerializerMethodField()
    denomination = serializers.IntegerField(write_only=True)
    message = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=6, decimal_places=2, source='amount')

    class Meta:
        model = Machine
        fields = ('state', 'message', 'denomination', 'amount', 'total_amount')

    def get_amount(self, obj):
        if obj.state == Machine.STATE_CURRENCY_INSERTED:
            return obj.last_transaction.total_transaction_amount
        else:
            return Decimal(0)

    def validate_denomination(self, denomination):
        if denomination not in MachineTransaction.DENOMINATOION_CHOICES_DICT.keys():
            raise ValidationError("Please enter a valid denomination")
        return denomination

    def validate(self, attrs):
        validated_data = super(AddCurrencySerializer, self).validate(attrs)
        if self.instance.state == Machine.STATE_OUT_OF_STOCK:
            raise ValidationError("Vending Machine is out of stock")

        transaction_data = {
            "action": MachineTransaction.ACTION_INSERT_DENOMINATION,
            "denomination": validated_data.pop('denomination', None),
            "activity_log": ""
        }
        self.transaction_serializer = TransactionSerializer(data=transaction_data,
                                                            context={
                                                                "machine": self.instance
                                                            })
        self.transaction_serializer.is_valid(raise_exception=True)
        return validated_data

    def update(self, instance, validated_data):
        transaction_obj = self.transaction_serializer.save()
        validated_data['state'] = Machine.STATE_CURRENCY_INSERTED
        validated_data['last_transaction'] = transaction_obj
        validated_data['amount'] = instance.amount + transaction_obj.amount
        validated_data['message'] = transaction_obj.activity_log
        return super(AddCurrencySerializer, self).update(instance, validated_data)


class UserCancelTransactionSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display', read_only=True)
    amount = serializers.SerializerMethodField()
    message = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=6, decimal_places=2, source='amount')

    class Meta:
        model = Machine
        fields = ('state', 'message', 'amount', 'total_amount')

    def get_amount(self, obj):
        if obj.state == Machine.STATE_CURRENCY_INSERTED:
            return obj.last_transaction.total_transaction_amount
        else:
            return Decimal(0)


    def validate(self, attrs):
        validated_date = super(UserCancelTransactionSerializer, self).validate(attrs)
        if self.instance.state != Machine.STATE_CURRENCY_INSERTED:
            raise ValidationError("No transaction to cancel")
        validated_date['state'] = Machine.STATE_READY
        transaction_data = {
            "action": MachineTransaction.ACTION_USER_CANCEL,
            "activity_log": ""
        }
        self.transaction_serializer = TransactionSerializer(data=transaction_data,
                                                            context={
                                                                "machine": self.instance
                                                            })
        self.transaction_serializer.is_valid(raise_exception=True)
        return validated_date

    def update(self, instance, validated_data):
        transaction_obj = self.transaction_serializer.save()
        validated_data['last_transaction'] = transaction_obj
        validated_data['amount'] = instance.amount - transaction_obj.amount
        validated_data['message'] = transaction_obj.activity_log
        return super(UserCancelTransactionSerializer, self).update(instance, validated_data)


class UserDispenseProductSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display', read_only=True)
    amount = serializers.SerializerMethodField()
    message = serializers.CharField(read_only=True)
    product = serializers.IntegerField(write_only=True, required=True)
    total_amount = serializers.DecimalField(max_digits=6, decimal_places=2, source='amount')

    class Meta:
        model = Machine
        fields = ('state', 'message', 'amount', 'product', 'total_amount')

    def get_amount(self, obj):
        if obj.state == Machine.STATE_CURRENCY_INSERTED:
            return obj.last_transaction.total_transaction_amount
        else:
            return Decimal(0)

    def validate(self, attrs):
        validated_date = super(UserDispenseProductSerializer, self).validate(attrs)
        if self.instance.state != Machine.STATE_CURRENCY_INSERTED:
            raise ValidationError("Please insert money before selecting any item")
        validated_date['state'] = Machine.STATE_READY
        transaction_data = {
            "action": MachineTransaction.ACTION_SELECT_ITEM,
            "activity_log": "",
            "product": validated_date.pop('product', None),
        }
        self.transaction_serializer = TransactionSerializer(data=transaction_data,
                                                            context={
                                                                "machine": self.instance
                                                            })
        self.transaction_serializer.is_valid(raise_exception=True)
        return validated_date

    def update(self, instance, validated_data):
        transaction_obj = self.transaction_serializer.save()
        print(transaction_obj.__dict__)
        if transaction_obj.action == MachineTransaction.ACTION_REFUND:
            validated_data['amount'] = instance.amount - transaction_obj.amount
        validated_data['last_transaction'] = transaction_obj
        validated_data['message'] = transaction_obj.activity_log
        if not Products.objects.filter(quantity__gt=0).exists():
            validated_data['state'] = Machine.STATE_OUT_OF_STOCK
        return super(UserDispenseProductSerializer, self).update(instance, validated_data)


class WithdrawAmountSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display', read_only=True)
    amount = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    withdraw_amount = serializers.DecimalField(max_digits=6, decimal_places=2, write_only=True, required=True)
    message = serializers.CharField(read_only=True)
    total_amount = serializers.DecimalField(max_digits=6, decimal_places=2, source='amount')

    class Meta:
        fields = ('withdraw_amount', 'state', 'message', 'amount', 'total_amount')
        model = Machine

    def get_amount(self, obj):
        if obj.state == Machine.STATE_CURRENCY_INSERTED:
            return obj.last_transaction.total_transaction_amount
        else:
            return Decimal(0)

    def validate_withdraw_amount(self, amount):
        if amount <=0:
            raise ValidationError("Please enter valid amount to withdraw")
        if amount > self.instance.amount:
            raise ValidationError("You can withdraw maximum Rs {} ".format(self.instance.amount))
        return amount

    def validate(self, attrs):
        validated_data = super(WithdrawAmountSerializer, self).validate(attrs)
        if self.instance.state == Machine.STATE_CURRENCY_INSERTED:
            raise ValidationError("You cannot withdraw money. A transaction is in progress")
        if not validated_data.get('withdraw_amount'):
            raise ValidationError("Please enter amount to withdraw")
        validated_data['amount'] = self.instance.amount - validated_data.get('withdraw_amount')
        transaction_data = {
            "action": MachineTransaction.ACTION_MAINTENANCE_WITHRAW_CURRENCY,
            "activity_log": "",
            "amount": validated_data.pop('withdraw_amount')
        }
        self.transaction_serializer = TransactionSerializer(data=transaction_data,
                                                            context={"machine": self.instance})
        self.transaction_serializer.is_valid(raise_exception=True)
        return validated_data

    def update(self, instance, validated_data):
        transaction_obj = self.transaction_serializer.save()
        validated_data['last_transaction'] = transaction_obj
        validated_data['amount'] = instance.amount - transaction_obj.amount
        validated_data['message'] = transaction_obj.activity_log
        return super(WithdrawAmountSerializer, self).update(instance, validated_data)


class AddProductSerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='get_state_display', read_only=True)
    product = serializers.IntegerField(write_only=True)
    quantity = serializers.IntegerField(required=False)
    message = serializers.CharField(read_only=True)

    class Meta:
        model = Machine
        fields = ('product', 'quantity', 'state', 'message')

    def validate_quantity(self, qty):
        if qty < 1:
            raise ValidationError('Please select a valid quantity for product')
        return qty

    def validate(self, attrs):
        validated_data = super(AddProductSerializer, self).validate(attrs)
        if self.instance.state == Machine.STATE_CURRENCY_INSERTED:
            raise ValidationError("You cannot add products. A transaction is in progress")
        transaction_data = {
            "action": MachineTransaction.ACTION_MAINTENANCE_ADD_PRODUCT,
            "product": validated_data.pop('product', None),
            "activity_log": "",
            "quantity": validated_data.pop('quantity')
        }
        self.transaction_serializer = TransactionSerializer(data=transaction_data,
                                                            context={"machine": self.instance})
        self.transaction_serializer.is_valid(raise_exception=True)
        return validated_data

    def update(self, instance, validated_data):
        transaction_obj = self.transaction_serializer.save()
        validated_data['last_transaction'] = transaction_obj
        validated_data['message'] = transaction_obj.activity_log
        return super(AddProductSerializer, self).update(instance, validated_data)


# class TransactionSerializer(serializers.ModelSerializer):
#     action = serializers.CharField(source = 'get_action_display')
#
#     class Meta:
#         model = MachineTransaction
#         fields = ('action', 'activity_log')