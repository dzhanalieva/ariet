from django.http import Http404, HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.views import APIView
from rest_framework import permissions, status, generics
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.conf import settings


from .models import Product, Category
from .serializers import ProductSerializer,  CategorySerializer, PurchaseSerializer
from user.permissions import IsVendorPermission, IsOwnerOrReadOnly
from django.db.models import Max, Min, Avg
import stripe
from django.db import transaction
from .models import Purchase


class ProductList(generics.ListAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'price']


class ProductSearchView(APIView):
    def get(self, request):
        query = request.GET.get('search')
        if query:
            products = Product.objects.filter(name__icontains=query)
        else:
            products = Product.objects.all()
        paginator = ProductPagination()
        paginated_products = paginator.paginate_queryset(products, request)
        serializer = ProductSerializer(paginated_products, many=True)
        return paginator.get_paginated_response(serializer.data)


class ProductPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ProductStatistics(APIView):
    def get(self, request):
        stats = Product.objects.aggregate(
            max_price=Max('price'),
            min_price=Min('price'),
            avg_price=Avg('price')
        )
        return Response(stats)


class ProductCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsVendorPermission]

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            product = Product.objects.create(
                vendor_id=request.data['vendor'],
                category_id=request.data['category'],
                name=request.data['name'],
                description=request.data['description'],
                price=request.data['price']
            )
            product.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get_object(self, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise Http404

    def get(self, request, id):
        product = self.get_object(id)
        serializer = ProductSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductUpdateAPIView(APIView):
    permission_classes = [IsVendorPermission, IsOwnerOrReadOnly]

    def get_object(self, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise Http404

    def put(self, request, id):
        snippet = self.get_object(id)
        serializer = ProductSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProductDeleteAPIView(APIView):
    permission_classes = [IsVendorPermission, IsOwnerOrReadOnly]

    def get_object(self, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise Http404

    def delete(self, request, id):
        snippet = self.get_object(id)
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CategoryUpdateAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def put(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            raise Http404
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryDeleteAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, pk):
        try:
            category = Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            raise Http404
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


stripe.api_key = settings.STRIPE_SECRET_KEY


class CreateCheckoutSession(APIView):
    def post(self, request, id):
        product = Product.objects.get(id=id)
        try:
            checkout_session = stripe.checkout.Session.create(
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': product.id,
                        },
                        'unit_amount': product.price
                    },
                    'quantity': 1
                }],
                mode= 'payment',
                success_url= 'https://example.com/checkout/success/',
                cancel_url= 'https://example.com/checkout/failed/',
            )
            purchase = Purchase.objects.create(user=request.user, product=product, price=product.price)
            return Response(checkout_session, status=status.HTTP_303_SEE_OTHER)
        except stripe.error.InvalidRequestError as e:
            return HttpResponse('Invalid request: {}'.format(str(e)), status=400)
        except Exception as e:
            return HttpResponse('Error: {}'.format(str(e)), status=500)


class PurchaseListAPIView(APIView):
    def get(self, request):
        purchases = Purchase.objects.filter(user=request.user).order_by('-purchase_date')
        serializer = PurchaseSerializer(purchases, many=True)
        return Response(serializer.data)
