from rest_framework import generics
from machine.models import Machine, Products, MachineTransaction
from machine.serializers import MachineSerializer, ProductSerializer, WithdrawAmountSerializer, AddProductSerializer, \
    AddCurrencySerializer, UserCancelTransactionSerializer, UserDispenseProductSerializer, TransactionSerializer

class ProductsView(generics.ListAPIView):
    queryset = Products.objects.all()
    serializer_class = ProductSerializer

class MachineStateApiView(generics.RetrieveAPIView):
    def get_object(self):
        return Machine.objects.select_related('last_transaction').last()

    serializer_class = MachineSerializer


class UserInsertCurrencySerializer(generics.UpdateAPIView):
    def get_object(self):
        return Machine.objects.select_related('last_transaction').last()

    serializer_class = AddCurrencySerializer


class UserCancelTransactionApiView(UserInsertCurrencySerializer):
    serializer_class = UserCancelTransactionSerializer


class UserDispenseProductApiVIew(UserInsertCurrencySerializer):
    serializer_class = UserDispenseProductSerializer


class AdminCashWithdrawApiView(UserInsertCurrencySerializer):
    serializer_class = WithdrawAmountSerializer


class AdminAddProductApiView(UserInsertCurrencySerializer):
    serializer_class = AddProductSerializer

class TransactionApiView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    queryset = MachineTransaction.objects.all().order_by('-id')



