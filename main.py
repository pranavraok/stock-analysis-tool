import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from fpdf import FPDF
import requests


# Function to process the stock name and automatically add .ns suffix
def get_full_stock_name(stock_name):
    if not stock_name.endswith(".ns"):
        stock_name += ".ns"
    return stock_name

# Example usage
user_input = input("Enter the stock name: ")  # User enters "RELIANCE"
full_stock_name = get_full_stock_name(user_input)

# Set the end date Automatically to the current date
end_date = datetime.today()

# To Calculate 365 days prior to the end date 
start_date = end_date - timedelta(days=365)

# To change the date format to YYYY-MM-DD 
end_date_str = end_date.strftime('%Y-%m-%d')
start_date_str = start_date.strftime('%Y-%m-%d')

# Download the Data of the stock from yfinance
data = yf.download(full_stock_name, start=start_date_str, end=end_date_str)

# Accessing only the closing prices
close_prices = data['Close']

# Calculate all-time high for the closing price
all_time_high = close_prices.max()
if isinstance(all_time_high, pd.Series):  
    all_time_high = all_time_high.iloc[0]

# Current Price - Ensure to get the last closing price correctly
current_price = close_prices.iloc[-1]  # Get the last closing price
if isinstance(current_price, pd.Series):  # Check if it's still a Series
    current_price = current_price.item()  # Convert to scalar

# Calculate the discount percentage
discount_percentage = ((all_time_high - current_price) / all_time_high) * 100

# Check if the discount percentage is a Series and convert it to a scalar if necessary
if isinstance(discount_percentage, pd.Series):  
    discount_percentage = discount_percentage.item()  # Ensure it's a scalar

# Check the discount conditions
if discount_percentage >= 0 and discount_percentage <= 65:
    alltimehigh_recommendation = "Recommend to Buy"
elif discount_percentage > 65 and discount_percentage <= 85:
    alltimehigh_recommendation = "Watch for support levels"
else:
    alltimehigh_recommendation = "Not the right time to buy, please wait."

# Calculating price changes and separating gains/losses
price_change = close_prices.diff()
gains = price_change.where(price_change > 0, 0)
losses = -price_change.where(price_change < 0, 0)

# Calculate averages of gains and losses using ewm() 
average_gains = gains.ewm(span=14, adjust=False).mean()
average_losses = losses.ewm(span=14, adjust=False).mean()

# Calculate the RSI
rs = average_gains / average_losses
rsi = 100 - (100 / (1 + rs))

# Ensure final_rsi_value is correctly assigned
final_rsi_value = rsi.iloc[-1]  # Get the last RSI value
if isinstance(final_rsi_value, pd.Series):  
    final_rsi_value = final_rsi_value.item()  # Ensure it is a scalar value

# Calculating the RSI-based recommendation
if final_rsi_value <= 41:
    rsi_recommendation = "Recommend to Buy (RSI is in the lower range)"
elif 42 <= final_rsi_value <= 62:
    rsi_recommendation = "Hold until RSI drops or reaches a support level"
else:
    rsi_recommendation = "Not recommended to Buy (RSI is high)"

# Create a Ticker object for the stock
stock = yf.Ticker(full_stock_name)

# Extract the trailing PE ratio
pe_ratio = stock.info.get("trailingPE")

# Check if PE ratio is available
if pe_ratio is not None:
    # PE Ratio conditions based on your criteria
    if 1 <= pe_ratio <= 30:
        pe_recommendation = "Very good buy (Not at all overvalued)"
    elif 31 <= pe_ratio <= 70:
        pe_recommendation = "Wait until support or RSI"
    else:
        pe_recommendation = "Do not buy (It is overvalued)"
else:
    pe_recommendation = "PE Ratio not available for this stock."

# Fetch the stock info
stock_info = stock.info

# Extract company details
sector = stock_info.get("sector", "Sector not available")

market_cap_raw = stock_info.get("marketCap", None)

# Convert market cap to crores if it exists
if market_cap_raw is not None:
    market_cap_crores = market_cap_raw / 10**7  # Convert to crores
    market_cap_text = f"{market_cap_crores:.2f} Crores"
else:
    market_cap_text = "Market cap not available"

company_name = stock_info.get("shortName", "Company Name not available")

# Fetch and shorten the company description to 200 characters
description = stock_info.get("longBusinessSummary", "Description not available")[:200] + "..."

# Primary function to get USD to INR conversion rate
def get_usd_to_inr():
    # Primary API
    url_primary = "https://api.exchangerate.host/latest?base=USD&symbols=INR"
    response_primary = requests.get(url_primary)
    
    if response_primary.status_code == 200:
        data_primary = response_primary.json()
        if "rates" in data_primary and "INR" in data_primary["rates"]:
            return data_primary["rates"]["INR"]

    # If primary fails, try a secondary API
    url_secondary = "https://open.er-api.com/v6/latest/USD"
    response_secondary = requests.get(url_secondary)
    
    if response_secondary.status_code == 200:
        data_secondary = response_secondary.json()
        if "rates" in data_secondary and "INR" in data_secondary["rates"]:
            return data_secondary["rates"]["INR"]
    
    # Fallback rate if both APIs fail
    print("Warning: Using fallback USD to INR rate of 83 due to API issues.")
    return 83  # Set your fallback rate here

# Convert to lakhs or crores as needed
def format_to_lakhs_or_crores(value_inr):
    if value_inr >= 1e7:  # Crores threshold
        return value_inr / 1e7, "Crores"
    elif value_inr >= 1e5:  # Lakhs threshold
        return value_inr / 1e5, "Lakhs"
    else:
        return value_inr, ""
    
usd_to_inr = get_usd_to_inr()

# Step 1: Fetch quarterly financial data
ticker = yf.Ticker(full_stock_name) 
income_statement = ticker.quarterly_financials


# Extract the last 4 quarters
dates = income_statement.columns[:4]
revenue = []
operating_profit = []
net_profit = []
for date in dates:
        try:
            revenue_inr, unit_rev = format_to_lakhs_or_crores(income_statement.loc["Total Revenue", date] * usd_to_inr)
            op_profit_inr, unit_op = format_to_lakhs_or_crores(income_statement.loc["Operating Income", date] * usd_to_inr)
            net_profit_inr, unit_np = format_to_lakhs_or_crores(income_statement.loc["Net Income", date] * usd_to_inr)
            
            revenue.append(revenue_inr)
            operating_profit.append(op_profit_inr)
            net_profit.append(net_profit_inr)
        except KeyError as e:
            print(f"Key error: {e} - some data might be missing for {date}")

# Convert dates to 'Month Year' format
formatted_dates = [datetime.strptime(str(date), '%Y-%m-%d %H:%M:%S').strftime('%b %Y') for date in dates]


stock_symbol = full_stock_name  
stock = yf.Ticker(stock_symbol)

# Fetch the quarterly income statement
income_statement_df = stock.quarterly_financials  # This should give you quarterly data

# Extract the last 2 quarters based on their datetime index
dates = income_statement_df.columns[:2]  # Get the last two quarters

# Extract relevant financial metrics
revenue_current = income_statement_df.loc['Total Revenue', dates[0]]
revenue_previous = income_statement_df.loc['Total Revenue', dates[1]]
operating_profit_current = income_statement_df.loc['Operating Income', dates[0]]
operating_profit_previous = income_statement_df.loc['Operating Income', dates[1]]
net_profit_current = income_statement_df.loc['Net Income', dates[0]]
net_profit_previous = income_statement_df.loc['Net Income', dates[1]]

# Comparison logic
revenue_comparison = revenue_current > revenue_previous
operating_profit_comparison = operating_profit_current > operating_profit_previous
net_profit_comparison = net_profit_current > net_profit_previous

overall_income_recomendation=['revenue_comparison','operating_profit_comparison','net_profit_comparison']

# Recommendation Logic
if revenue_comparison and operating_profit_comparison and net_profit_comparison:
    recommendation = " Recommended To Buy (Fundamentals Has Increased From The Previous Quarter)"
elif revenue_comparison:
    recommendation = "Buy At Your Own Risk (Net Profit And Operating Profit Is Less Than The Previous Quarter)"
else:
     recommendation = "Recommended Not To Buy (Fundamentals Has Decreased From The Previous Quarter)"

# Adding Final Conclusion
# Define futuristic sectors
futuristic_sectors = (
    "Renewable Energy", "Electric Vehicles", "Artificial Intelligence", "Machine Learning", "Healthcare",
    "Telemedicine", "E-commerce", "Logistics", "Fintech", "Cybersecurity", "Agritech", "EdTech","Consumer Defensive",
    "Space Technology", "Biotechnology", "Data Centre", "Water Management", "Smart Cities", "Infrastructure","Financial Services"
)

if (final_rsi_value <= 47) and (discount_percentage >= 0 and discount_percentage <= 75) and ((revenue_current > revenue_previous) and (operating_profit_current>operating_profit_previous) and (net_profit_current>net_profit_previous)):
    final_conclusion="This Stock Is Best For Swing Trading(Hold 2-3 Months)"
    
elif sector in futuristic_sectors and market_cap_crores>=7000 and 1 <= pe_ratio <= 30:
    final_conclusion="This Stock Is Best For Long Term Investment(1-2 Years)"
    
else:
    final_conclusion="This stock may not meet all criteria for swing trading or long-term investment.....Please Avoid "


# Plotting the bar graph
plt.figure(figsize=(10, 6))
bar_width = 0.2
positions = range(len(formatted_dates))

# Plotting the RSI
plt.figure(figsize=(10, 5))
plt.plot(rsi, label='RSI', color='blue')

# Adding horizontal lines for overbought and oversold levels
plt.axhline(70, linestyle='-', alpha=0.5, color='red', label='Overbought (70)')
plt.axhline(30, linestyle='-', alpha=0.5, color='green', label='Oversold (30)')

# Setting y-axis limits from 10 to 90
plt.ylim(10, 100)

# Annotating the final RSI value
final_rsi_value = rsi.iloc[-1].item()  
final_rsi_date = rsi.index[-1]          

if pd.notna(final_rsi_value):
    plt.annotate(f'Final RSI: {final_rsi_value:.2f}', 
                 xy=(final_rsi_date, final_rsi_value), 
                 xytext=(final_rsi_date, final_rsi_value + 5), 
                 arrowprops=dict(facecolor='black', arrowstyle='->'),
                 fontsize=10, color='black')

# Adding title, labels, and legend
plt.title(f'RSI for {full_stock_name}')
plt.xlabel('Date')
plt.ylabel('RSI')
plt.legend()
plt.grid()

# Save plot as image to include in the PDF
plot_filename1 = "rsi_plot.png"
plt.savefig(plot_filename1)
plt.close()  # Close the plot to free up memory


# Plotting bars for each metric
plt.bar(positions, revenue, width=bar_width, label=f'Revenue ({unit_rev})')
plt.bar([p + bar_width for p in positions], operating_profit, width=bar_width, label=f'Operating Profit ({unit_op})')
plt.bar([p + bar_width*2 for p in positions], net_profit, width=bar_width, label=f'Net Profit ({unit_np})')

# Labels and title
plt.xlabel("Quarters")
plt.ylabel(f"Amount in {unit_rev or unit_op or unit_np}")
plt.title("Income Statement - Revenue, Operating Profit, Net Profit (in Lakhs or Crores)")
plt.xticks([p + bar_width for p in positions], formatted_dates, rotation=0)
plt.legend()
plt.tight_layout()

# Save plot as image to include in the PDF
plot_filename2 = "income_statement.png"
plt.savefig(plot_filename2)
plt.close() # Close the plot to free up memory

# Create a custom PDF class that extends FPDF to include page numbers
class PDF(FPDF):
    def footer(self):
        self.set_y(-15)  # Position at 1.5 cm from bottom
        self.set_font('Arial', 'I', 8)  # Font style for footer
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')  # Centered page number

# Creating a PDF report using the custom PDF class
pdf = PDF('P','mm','A4')
pdf.add_page()

# Title
pdf.set_font("Arial", "B", 16)
pdf.cell(200, 10, f"Stock Analysis Report for {company_name}", ln=True, align="C")

# Add double underline
y = pdf.get_y()  # Get current y position
pdf.line(10, y + 5, 200, y + 5)  # Draw the line below the heading
pdf.line(10, y + 7, 200 ,y + 7)  # Draw the 2nd line 
pdf.ln(10)  # Add a line break to create space between the underline and the next text

# Add Company Information to PDF
pdf.set_font("Arial", "BU", 12)
pdf.set_text_color(255, 0, 0)  # Red for label
pdf.cell(40, 10, "1) COMPANY INFORMATION:", ln=True)

pdf.set_text_color(0, 0, 0)  # Black for content
pdf.set_font("Arial", "", 10)
pdf.cell(150, 10, f"   Name: {company_name}", ln=True)
x = 15  # Starting x-coordinate (same as text position)
y = pdf.get_y()  # Current y position after text
pdf.line(x-1, y-2, x + 9, y-2)  

pdf.cell(150, 10, f"   Sector: {sector}", ln=True)
x = 15  # Starting x-coordinate (same as text position)
y = pdf.get_y()  # Current y position after text
pdf.line(x-1, y-2, x + 10, y-2)  

pdf.cell(200, 10, f"   Market Cap: {market_cap_text}", ln=True)
x = 15  # Starting x-coordinate (same as text position)
y = pdf.get_y()  # Current y position after text
pdf.line(x-1, y-2, x + 18, y-2)  

pdf.cell(200, 10, "", ln=True)  # Add space before description
pdf.multi_cell(0, 10, f" Description: {description}")
x = 15  # Starting x-coordinate (same as text position)
y = pdf.get_y()  # Current y position after text
pdf.line(x-2, y-12, x + 16, y-12)  

# Set font once for consistent font size
pdf.set_font("Arial", "BU", 12)

# Set color for the "All-Time High" label
pdf.set_text_color(255, 0, 0)  # Red for the label
pdf.cell(40, 25, "2) ALL TIME HIGH :", ln=False)  # Label without line break

# Set font once for consistent font size
pdf.set_font("Arial", "B", 12)

# Reset color for the content
pdf.set_text_color(0, 0, 0)  # Black for the actual high value
pdf.cell(10, 25, f"      (INR {all_time_high:.2f} )", ln=True)  # Content with line break

# Add current price and Recommendation below All-Time High
pdf.set_font("Arial", "", 10)  # Reset font size
pdf.cell(200, -5, f"   Current Price: INR {current_price:.2f}", ln=True)
pdf.set_font("Arial", "", 10)  # Smaller font for recommendation
pdf.cell(200, 20, f"   Recommendation: {alltimehigh_recommendation}", ln=True)

# Set font once for consistent font size
pdf.set_font("Arial", "BU", 12)

# Set color for the "RSI Levels" label
pdf.set_text_color(255, 0, 0)  # Red for the label
pdf.cell(40, 17, "3) RELATIVE STRENGTH INDEX (RSI) : ", ln=False)  # Label without line break

# Add RSI Plot to the PDF
pdf.image(plot_filename1, x=10, y=165, w=180)

# Adding the RSI-based recommendation to the PDF
pdf.set_font("Arial", "", 10)  # Set font size for recommendation text
pdf.set_text_color(0, 0, 0)  # To set Black color
pdf.cell(0, 40, f"   RSI Recommendation: {rsi_recommendation}", ln=True, align='L')  # Left align for RSI recommendation

# Adding Another Page 2
pdf.add_page()

# Adding the PE ratio and recommendation to the PDF
pdf.set_font("Arial", "BU", 12)  # Set font for PE Ratio heading

# Set color for the "PE Ratio" label
pdf.set_y(10)
pdf.set_text_color(255, 0, 0)  # Red for the label
pdf.cell(40, 0, "4) P/E RATIO :", ln=False)  # Label without line break

pdf.set_font("Arial",'B',12)

# Reset color for the content
pdf.set_y(10)
pdf.set_text_color(0, 0, 0)  # Black for the actual PE value
pdf.cell(-5, 0, f"                              ( {pe_ratio:.2f} )", ln=True)  # Content with line break

# Adding recommendation below PE Ratio
pdf.set_y(20)
pdf.set_font("Arial", "", 10)  # Reset font size
pdf.cell(200, 0, f"   Recommendation: {pe_recommendation}", ln=True)

# Adding Income Statement Under PE Raio 
pdf.set_font("Arial", "BU", 12)
pdf.set_text_color(255,0,0)
pdf.cell(0, 35, "5) INCOME STATEMENT - RECENT QUARTERS (INR)", 0, 1, "L")

# Adding the recommendation from Income Statement to the PDF
pdf.set_text_color(0, 0, 0)
pdf.set_font("Arial", size=10)
pdf.cell(200, -5, txt="Fundamental Recommendation: " + recommendation, ln=True , align='C')

# Adding The Image To The Pdf 
pdf.image(plot_filename2, x=10, y=60, w=180)

# Adding The Final Conclusion To The Pdf 
pdf.set_y(175)
pdf.set_font("Arial","BU",15)
pdf.set_text_color(255,0,0)
pdf.cell(0, 10, "FINAL RECOMMENDATION", 0, 1, "C")

pdf.set_y(190)
pdf.set_text_color(0,0,0)
pdf.set_font("Arial","B",12)
pdf.cell(0,10,final_conclusion, 0, 1, "C")

# Save the PDF
pdf.output("Stock_Analysis_Report.pdf")

print("PDF report with RSI plot and analysis generated successfully.")
