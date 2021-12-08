# -*- coding: utf-8 -*-

post_code = 'se152dy'

radius = 0.5  # in miles
minimum_beds = 1
maximum_beds = 4  # these values are inclusive
percentile = 0.8  # comps percentile to use as a decimal

auto_filter_on = 'Y'
save_flag = 'Y'
"""this is either 'Y' or 'N' """
website = "http://api.zoopla.co.uk/api/v1/property_listings.js"

import functions as fn

rental_comps = fn.full_comps_calc(website, post_code, radius, minimum_beds, maximum_beds, "rent", percentile,
                                  auto_filter_on, save_flag)

sales_comps = fn.full_comps_calc(website, post_code, radius, minimum_beds, maximum_beds, "sale", percentile,
                                 auto_filter_on, save_flag)

