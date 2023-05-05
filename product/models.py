from django.db import models
from user.models import Vendor, Customer
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)

    def __str__(self):
        return self.name


class Product(models.Model):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField()
    price = models.IntegerField(null=False, blank=False)

    def __str__(self):
        return self.name


class Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    product = models.ManyToManyField(Product)

    def __str__(self):
        return f'{self.customer.email}s cart'


class Purchase(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    price = models.IntegerField(null=False, blank=False)
    purchase_date = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'{self.product} purchased by {self.user} on {self.purchase_date}'


