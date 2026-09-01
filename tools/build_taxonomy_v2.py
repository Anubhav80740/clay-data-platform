# Parse Non-Tech and calculate Tech industries
NON_TECH_RAW = """Abrasives and Nonmetallic Minerals Manufacturing
Accessible Architecture and Design
Accommodation Services
Accounting
Administration of Justice
Administrative and Support Services
Advertising Services
Agricultural Chemical Manufacturing
"Agriculture, Construction, Mining Machinery Manufacturing"
"Air, Water, and Waste Program Management"
Airlines and Aviation
Alternative Dispute Resolution
Alternative Medicine
Ambulance Services
Amusement Parks and Arcades
Animal Feed Manufacturing
Animation
Animation and Post-production
Apparel and Fashion
Apparel Manufacturing
Architectural and Structural Metal Manufacturing
Architecture and Planning
Armed Forces
Artists and Writers
Arts and Crafts
Audio and Video Equipment Manufacturing
Automotive
Aviation & Aerospace
Aviation and Aerospace Component Manufacturing
Baked Goods Manufacturing
Banking
"Bars, Taverns, and Nightclubs"
"Bed-and-Breakfasts, Hostels, Homestays"
Beverage Manufacturing
Biomass Electric Power Generation
Blogs
"Boilers, Tanks, and Shipping Container Manufacturing"
Book and Periodical Publishing
Book Publishing
Breweries
Broadcast Media Production and Distribution
Building Construction
Building Equipment Contractors
Building Finishing Contractors
Building Materials
Building Structure and Exterior Contractors
Business Consulting and Services
Business Content
Business Intelligence Platforms
Business Supplies and Equipment
Capital Markets
Caterers
Chemical Manufacturing
Chemical Raw Materials Manufacturing
Child Day Care Services
Chiropractors
Civic and Social Organizations
Civil Engineering
"Claims Adjusting, Actuarial Services"
Clay and Refractory Products Manufacturing
Coal Mining
Collection Agencies
Commercial and Industrial Equipment Rental
Commercial and Industrial Machinery Maintenance
Commercial and Service Industry Machinery Manufacturing
Commercial Real Estate
Communications Equipment Manufacturing
Community Development and Urban Planning
Community Services
Conservation Programs
Construction
Construction Hardware Manufacturing
Consumer Goods
Consumer Goods Rental
Consumer Services
Cosmetics
Cosmetology and Barber Schools
Courts of Law
Credit Intermediation
Dairy
Dairy Product Manufacturing
Dance Companies
Defense & Space
Defense and Space Manufacturing
Dentists
Design
Design Services
Digital Accessibility Services
Distilleries
E-Learning
E-Learning Providers
Economic Programs
Education
Education Administration Programs
Education Management
Electric Lighting Equipment Manufacturing
Electric Power Generation
"Electric Power Transmission, Control, and Distribution"
Electrical Equipment Manufacturing
Electronic and Precision Equipment Maintenance
Emergency and Relief Services
Engineering Services
Engines and Power Transmission Equipment Manufacturing
Entertainment
Entertainment Providers
Environmental Quality Programs
Environmental Services
Equipment Rental Services
Events Services
Executive Offices
Executive Search Services
Fabricated Metal Products
Facilities Services
Farming
"Farming, Ranching, Forestry"
Fashion Accessories Manufacturing
Financial Services
Fine Art
Fine Arts Schools
Fire Protection
Fisheries
Flight Training
Food & Beverages
Food and Beverage Manufacturing
Food and Beverage Retail
Food and Beverage Services
Food Production
Footwear Manufacturing
Forestry and Logging
Freight and Package Transportation
Fruit and Vegetable Preserves Manufacturing
Fundraising
Funds and Trusts
Furniture
Furniture and Home Furnishings Manufacturing
Gambling Facilities and Casinos
Generation
Geothermal Electric Power
Glass Product Manufacturing
"Glass, Ceramics and Concrete Manufacturing"
Golf Courses and Country Clubs
Government Administration
Government Relations
Government Relations Services
Graphic Design
Ground Passenger Transportation
Health and Human Services
"Health, Wellness and Fitness"
Higher Education
"Highway, Street, and Bridge Construction"
Historical Sites
Holding Companies
Home Health Care Services
Horticulture
Hospitality
Hospitals
Hospitals and Health Care
Hotels and Motels
Household and Institutional Furniture Manufacturing
Household Appliance Manufacturing
Household Services
Housing and Community Development
Housing Programs
Human Resources
Human Resources Services
HVAC and Refrigeration Equipment Manufacturing
Hydroelectric Power Generation
Import and Export
Individual and Family Services
Industrial Machinery Manufacturing
Industry Associations
Insurance
Insurance Agencies and Brokerages
Insurance and Employee Benefit Funds
Insurance Carriers
Interior Design
International Affairs
International Trade and Development
Investment Advice
Investment Banking
Investment Management
Janitorial Services
Landscaping Services
Language Schools
Laundry and Drycleaning Services
Law Enforcement
Law Practice
Leasing Non-residential Real Estate
Leasing Residential Real Estate
Leather Product Manufacturing
Legal Services
Legislative Offices
"Leisure, Travel & Tourism"
Libraries
Loan Brokers
Luxury Goods and Jewelry
Machinery Manufacturing
Manufacturing
Maritime
Maritime Transportation
Market Research
Marketing Services
Mattress and Blinds Manufacturing
Measuring and Control Instrument Manufacturing
Meat Products Manufacturing
Mechanical or Industrial Engineering
Media Production
Medical and Diagnostic Laboratories
Medical Devices
Medical Equipment Manufacturing
Medical Practices
Mental Health Care
Metal Ore Mining
Metal Treatments
"Metal Valve, Ball, and Roller Manufacturing"
Metalworking Machinery Manufacturing
Military and International Affairs
Mining
Mobile Food Services
Mobile Gaming Apps
Motor Vehicle Manufacturing
Motor Vehicle Parts
Movies and Sound Recording
"Movies, Videos and Sound"
Museums
"Museums, Historical Sites, and Zoos"
Music
Musicians
Natural Gas Distribution
Newspaper Publishing
Non-profit Organization Management
Non-profit Organizations
Nonmetallic Mineral Mining
Nonresidential Building Construction
Nuclear Electric Power Generation
Nursing Homes and Residential Care Facilities
Office Administration
Office Furniture and Fixtures Manufacturing
Oil and Gas
"Oil, Gas, and Mining"
Online and Mail Order Retail
Online Audio and Video Media
Online Media
Operations Consulting
Optometrists
Outpatient Care Centers
Outsourcing and Offshoring Consulting
Outsourcing/Offshoring
Packaging and Containers
Packaging and Containers Manufacturing
"Paint, Coating, and Adhesive Manufacturing"
Paper and Forest Product Manufacturing
Paper and Forest Products
Performing Arts
Performing Arts and Spectator Sports
Periodical Publishing
Personal and Laundry Services
Personal Care Product Manufacturing
Personal Care Services
Pet Services
Pharmaceutical Manufacturing
Philanthropic Fundraising Services
Philanthropy
Photography
"Physical, Occupational and Speech Therapists"
Physicians
Plastics and Rubber Product Manufacturing
Plastics Manufacturing
Political Organizations
Primary and Secondary Education
Primary Metal Manufacturing
Printing Services
Professional Organizations
Professional Services
Professional Training and Coaching
Program Development
Public Assistance Programs
Public Health
Public Policy
Public Policy Offices
Public Relations and Communications Services
Public Safety
Radio and Television Broadcasting
Rail Transportation
Railroad Equipment Manufacturing
Ranching
Real Estate
Real Estate Agents and Brokers
Real Estate and Equipment Rental Services
Recreational Facilities
Religious Institutions
Renewable Energy Equipment Manufacturing
Renewable Energy Power Generation
Renewables & Environment
Repair and Maintenance
Research
Research Services
Residential Building Construction
Restaurants
Retail
Retail Apparel and Fashion
"Retail Appliances, Electrical, and Electronic Equipment"
Retail Art Dealers
Retail Art Supplies
Retail Books and Printed News
Retail Building Materials and Garden Equipment
Retail Florists
Retail Furniture and Home Furnishings
Retail Gasoline
Retail Groceries
Retail Health and Personal Care Products
Retail Luxury Goods and Jewelry
Retail Motor Vehicles
Retail Musical Instruments
Retail Office Equipment
Retail Office Supplies and Gifts
Retail Pharmacies
Retail Recyclable Materials & Used Merchandise
Reupholstery and Furniture Repair
Rubber Products Manufacturing
School and Employee Bus Services
Seafood Product Manufacturing
Securities and Commodity Exchanges
Security and Investigations
Security Guards and Patrol Services
Security Systems Services
Services for Renewable Energy
Services for the Elderly and Disabled
Sheet Music Publishing
Shipbuilding
Shuttles and Special Needs Transportation Services
Sightseeing Transportation
Soap and Cleaning Product Manufacturing
Solar Electric Power Generation
Sound Recording
Specialty Trade Contractors
Spectator Sports
Sporting Goods
Sporting Goods Manufacturing
Sports and Recreation Instruction
Sports Teams and Clubs
Spring and Wire Product Manufacturing
Staffing and Recruiting
Steam and Air-Conditioning Supply
Strategic Management Services
Subdivision of Land
Sugar and Confectionery Product Manufacturing
Surveying and Mapping Services
Taxi and Limousine Services
Technical and Vocational Training
Telephone Call Centers
Temporary Help Services
Textile Manufacturing
Theater Companies
Think Tanks
Tobacco
Tobacco Manufacturing
Translation and Localization
Transportation Equipment Manufacturing
Transportation Programs
"Transportation, Logistics, Supply Chain and Storage"
Transportation/Trucking/Railroad
Travel Arrangements
Truck Transportation
Trusts and Estates
Turned Products and Fastener Manufacturing
Urban Transit Services
Utilities
Utilities Administration
Utility System Construction
Vehicle Repair and Maintenance
Venture Capital and Private Equity Principals
Veterinary
Veterinary Services
Vocational Rehabilitation Services
Warehousing
Warehousing and Storage
Waste Collection
Waste Treatment and Disposal
Water Supply and Irrigation Systems
"Water, Waste, Steam, and Air Conditioning Services"
Wellness and Fitness Services
Wholesale
Wholesale Alcoholic Beverages
Wholesale Apparel and Sewing Supplies
"Wholesale Appliances, Electrical, and Electronics"
Wholesale Building Materials
Wholesale Chemical and Allied Products
Wholesale Computer Equipment
Wholesale Drugs and Sundries
Wholesale Food and Beverage
Wholesale Footwear
Wholesale Furniture and Home Furnishings
"Wholesale Hardware, Plumbing, Heating Equipment"
Wholesale Import and Export
Wholesale Luxury Goods and Jewelry
Wholesale Machinery
Wholesale Metals and Minerals
Wholesale Motor Vehicles and Parts
Wholesale Paper Products
Wholesale Petroleum and Petroleum Products
Wholesale Raw Farm Products
Wholesale Recyclable Materials
Wind Electric Power Generation
Wine and Spirits
Wineries
Wireless Services
Wood Product Manufacturing
Writing and Editing
Zoos and Botanical Gardens"""

from clay_taxonomy import ALL_CLAY_INDUSTRIES, ALL_CLAY_COUNTRIES

def run():
    non_tech_set = set(line.strip().strip('"') for line in NON_TECH_RAW.strip().split('\n') if line.strip())
    non_tech_list = [ind for ind in ALL_CLAY_INDUSTRIES if ind in non_tech_set]
    tech_list = [ind for ind in ALL_CLAY_INDUSTRIES if ind not in non_tech_set]
    
    print(f"Total Clay Industries: {len(ALL_CLAY_INDUSTRIES)}")
    print(f"Non-Tech Industries: {len(non_tech_list)}")
    print(f"Tech Industries: {len(tech_list)}")
    
    content = f"""# Auto-generated taxonomy for Clay Industries & Countries
ALL_CLAY_INDUSTRIES = {repr(ALL_CLAY_INDUSTRIES)}

NON_TECH_INDUSTRIES = {repr(non_tech_list)}

TECH_INDUSTRIES = {repr(tech_list)}

ALL_CLAY_COUNTRIES = {repr(ALL_CLAY_COUNTRIES)}

DEFAULT_17_INDUSTRIES = [
    "Telecommunications",
    "Appliances, Electrical, and Electronics Manufacturing",
    "Renewable Energy Semiconductor Manufacturing",
    "Information Services",
    "Biotechnology Research",
    "Automation Machinery Manufacturing",
    "Consumer Electronics",
    "Media & Telecommunications",
    "Biotechnology",
    "Industrial Automation",
    "Nanotechnology Research",
    "Robotics Engineering",
    "Telecommunications Carriers",
    "Space Research and Technology",
    "Climate Technology Product Manufacturing",
    "Climate Data and Analytics",
    "Satellite Telecommunications"
]
"""
    with open("clay_taxonomy.py", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Updated clay_taxonomy.py successfully.")

if __name__ == "__main__":
    run()
