class MarketingGenerator:
    def __init__(self):
        self.name = "marketing_generator"
        self.description = "Generates marketing copy, Facebook ads, and social media posts based on product information."

    def execute(self, product_info):
        name = product_info.get('product_name', 'product')
        desc = product_info.get('description', '')
        price = product_info.get('price', '')

        facebook_ad = f"""🔥 Discover {name}! {desc[:100]}... 
✅ Quality at a great price {price}
➡️ Click for more info!"""

        instagram_post = f"""✨ {name} – exactly what you need! 
{desc[:120]}...
Price: {price}
#product #new #musthave"""

        seo_blog = f"""# {name}: Complete Guide

{name} is a product that {desc[:200]}... 
Why choose it? 
- High quality
- Great price {price}
- Excellent reviews

Visit our store and see for yourself!"""

        return {
            'facebook_ad': facebook_ad,
            'instagram_post': instagram_post,
            'seo_blog': seo_blog
   }
