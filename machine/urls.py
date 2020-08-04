from django.urls import path
from machine import views as machine_views


urlpatterns = [
    path('products', machine_views.ProductsView.as_view()),
    path('state', machine_views.MachineStateApiView.as_view()),



    path('user_insert_currency', machine_views.UserInsertCurrencySerializer.as_view()),
    path('user_cancel_transaction', machine_views.UserCancelTransactionApiView.as_view()),
    path('user_dispense_product', machine_views.UserDispenseProductApiVIew.as_view()),
    path('admin_withdraw', machine_views.AdminCashWithdrawApiView.as_view()),
    path('admin_add_product', machine_views.AdminAddProductApiView.as_view()),
    path('admin_transaction_list', machine_views.TransactionApiView.as_view()),

]


