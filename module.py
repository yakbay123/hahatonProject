import json
import datetime

class MarketplaceSorter:
    def __init__(self, products):
        self.products = products

    def filter_by_price_range(self, min_price=0, max_price=float('inf')):
        return [product for product in self.products 
                if min_price <= product['price'] <= max_price]
    
    def filter_by_rating(self, min_rating=0):
        return [product for product in self.products 
                if product['rating'] >= min_rating]
    
    def search_by_title(self, search_term):
        return [product for product in self.products 
                if search_term.lower() in product['title'].lower()]

