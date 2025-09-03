from graphs import presentation_super_agent,behaviour_analyst_super_agent, database_agent_super_agent
from IPython.display import Image, display
import json
import ast

def main():
    # presentation agent output
    insights = """
        Step: Retrieve the total spending and the total number of transactions for a specific user.
        Query: SELECT SUM(Amount_EGP) AS Total_Spending, COUNT(Transaction_ID) AS Total_Transactions FROM transactions_table WHERE User_ID = 1;
        Results:    Total_Spending  Total_Transactions
        0          122610                 150
        ------------------------------
        Step: Calculate the mean, median, minimum, and maximum transaction amounts for a specific user.
        Query: SELECT AVG(Amount_EGP) AS Mean_Amount, MIN(Amount_EGP) AS Min_Amount, MAX(Amount_EGP) AS Max_Amount, (SELECT Amount_EGP FROM transactions_table WHERE User_ID = 1 ORDER BY Amount_EGP LIMIT 1 OFFSET (SELECT COUNT(*) / 2 FROM transactions_table WHERE User_ID = 1)) AS Median_Amount FROM transactions_table WHERE User_ID = 1 LIMIT 1;
        Results:    Mean_Amount  Min_Amount  Max_Amount  Median_Amount
        0        817.4          65        4595            425
        ------------------------------
        Step: Determine the mode of transaction amount for a specific user.
        Query: SELECT Amount_EGP FROM transactions_table WHERE User_ID = 1 GROUP BY Amount_EGP ORDER BY COUNT(*) DESC LIMIT 1;
        Results:    Amount_EGP
        0          70
        ------------------------------
        Step: Identify the top spending categories for a specific user, including the total amount spent and the number of transactions in each category.
        Query: SELECT Category, SUM(Amount_EGP) AS Total_Amount_Spent, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 GROUP BY Category ORDER BY Total_Amount_Spent DESC;
        Results:         Category  Total_Amount_Spent  Number_Of_Transactions
        0       Shopping               81110                      47
        1  Entertainment               19105                      34
        2         Travel               12575                       8
        3  Food & Dining                7415                      45
        4      Education                1510                      12
        5         Health                 895                       4
        ------------------------------
        Step: Calculate the mean, median, minimum, and maximum transaction amounts for each spending category for a specific user.
        Query: SELECT Category, AVG(Amount_EGP) AS Mean_Amount, MIN(Amount_EGP) AS Min_Amount, MAX(Amount_EGP) AS Max_Amount FROM transactions_table WHERE User_ID = 1 GROUP BY Category;
        Results:         Category  Mean_Amount  Min_Amount  Max_Amount
        0      Education   125.833333          75         180
        1  Entertainment   561.911765         115        1295
        2  Food & Dining   164.777778          65         330
        3         Health   223.750000          70         320
        4       Shopping  1725.744681         500        4595
        5         Travel  1571.875000         125        3660
        ------------------------------
        Step: Find the most frequent spending category (mode) for a specific user.
        Query: SELECT Category FROM transactions_table WHERE User_ID = 1 GROUP BY Category ORDER BY COUNT(*) DESC LIMIT 1;
        Results:    Category
        0  Shopping
        ------------------------------
        Step: Identify the top locations (City and Neighborhood) where a specific user spends, including total amount and transaction count for each location.
        Query: SELECT City, Neighborhood, SUM(Amount_EGP) AS Total_Amount_Spent, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 GROUP BY City, Neighborhood ORDER BY Total_Amount_Spent DESC;
        Results:                   City                 Neighborhood  Total_Amount_Spent  Number_Of_Transactions
        0               Online                       Online               52585                      59
        1                Cairo                   Heliopolis               32990                      14
        2                Cairo                    Nasr City               14515                       7
        3                Cairo  Cairo International Airport               12010                       4
        4                Cairo                     Downtown                6260                      30
        5                Cairo                      Zamalek                1350                      15
        6                 Giza             Giza (CU Campus)                1080                       9
        7                Cairo                       Ramses                 855                       5
        8           Alexandria                  Al Mesallah                 565                       4
        9  6th of October City               Mall of Arabia                 400                       3
        ------------------------------
        Step: Calculate the mean, median, minimum, and maximum transaction amounts for each City and Neighborhood for a specific user.
        Query: SELECT City, Neighborhood, AVG(Amount_EGP) AS Mean_Amount, MIN(Amount_EGP) AS Min_Amount, MAX(Amount_EGP) AS Max_Amount FROM transactions_table WHERE User_ID = 1 GROUP BY City, Neighborhood;
        Results:                   City                 Neighborhood  Mean_Amount  Min_Amount  Max_Amount
        0  6th of October City               Mall of Arabia   133.333333         115         150
        1           Alexandria                  Al Mesallah   141.250000         125         155
        2                Cairo  Cairo International Airport  3002.500000        1990        3660
        3                Cairo                     Downtown   208.666667         160         330
        4                Cairo                   Heliopolis  2356.428571          70        4595
        5                Cairo                    Nasr City  2073.571429        1355        2800
        6                Cairo                       Ramses   171.000000          70         320
        7                Cairo                      Zamalek    90.000000          65         180
        8                 Giza             Giza (CU Campus)   120.000000          75         180
        9               Online                       Online   891.271186         250        2535
        ------------------------------
        Step: Find the most frequent spending location (mode of Neighborhood and City) for a specific user.
        Query: SELECT City, Neighborhood FROM transactions_table WHERE User_ID = 1 GROUP BY City, Neighborhood ORDER BY COUNT(*) DESC LIMIT 1;
        Results:      City Neighborhood
        0  Online       Online
        ------------------------------
        Step: Identify the top stores where a specific user spends, including total amount and transaction count for each store.
        Query: SELECT Store_Name, SUM(Amount_EGP) AS Total_Amount_Spent, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 GROUP BY Store_Name ORDER BY Total_Amount_Spent DESC;
        Results:                         Store_Name  Total_Amount_Spent  Number_Of_Transactions
        0        iStore Egypt – Heliopolis               24090                       8
        1                   Jumia (Online)               21250                      15
        2      City Stars Mall – Nasr City               14515                       7
        3     Amazon Egypt (Souq) (Online)               12630                      13
        4   EgyptAir – Cairo Intl. Airport               12010                       4
        5       PlayStation Store (Online)               11115                      14
        6    Raya Electronics – Heliopolis                8625                       4
        7                   Steam (Online)                7590                      17
        8        Domino's Pizza – Downtown                3890                      18
        9             Pizza Hut – Downtown                2370                      12
        10       Cairo University Bookshop                1080                       9
        11             Starbucks – Zamalek                 920                      12
        12          Seif Pharmacy – Ramses                 620                       2
        13             Go Bus – Alexandria                 565                       4
        14       Diwan Bookstore – Zamalek                 430                       3
        15       Cineplex – Mall of Arabia                 400                       3
        16  El Ezaby Pharmacy – Heliopolis                 275                       2
        17     Koshary Abou Tarek – Ramses                 235                       3
        ------------------------------
        Step: Calculate the mean, median, minimum, and maximum transaction amounts for each store for a specific user.
        Query: SELECT Store_Name, AVG(Amount_EGP) AS Mean_Amount, MIN(Amount_EGP) AS Min_Amount, MAX(Amount_EGP) AS Max_Amount FROM transactions_table WHERE User_ID = 1 GROUP BY Store_Name;
        Results:                         Store_Name  Mean_Amount  Min_Amount  Max_Amount
        0     Amazon Egypt (Souq) (Online)   971.538462         510        1750
        1        Cairo University Bookshop   120.000000          75         180
        2        Cineplex – Mall of Arabia   133.333333         115         150
        3      City Stars Mall – Nasr City  2073.571429        1355        2800
        4        Diwan Bookstore – Zamalek   143.333333          90         180
        5        Domino's Pizza – Downtown   216.111111         160         330
        6   EgyptAir – Cairo Intl. Airport  3002.500000        1990        3660
        7   El Ezaby Pharmacy – Heliopolis   137.500000          70         205
        8              Go Bus – Alexandria   141.250000         125         155
        9                   Jumia (Online)  1416.666667         500        2535
        10     Koshary Abou Tarek – Ramses    78.333333          70          95
        11            Pizza Hut – Downtown   197.500000         170         240
        12      PlayStation Store (Online)   793.928571         450        1295
        13   Raya Electronics – Heliopolis  2156.250000        1430        3890
        14          Seif Pharmacy – Ramses   310.000000         300         320
        15             Starbucks – Zamalek    76.666667          65          95
        16                  Steam (Online)   446.470588         250         695
        17       iStore Egypt – Heliopolis  3011.250000        1700        4595
        ------------------------------
        Step: Find the most frequent store (mode) for a specific user.
        Query: SELECT Store_Name FROM transactions_table WHERE User_ID = 1 GROUP BY Store_Name ORDER BY COUNT(*) DESC LIMIT 1;
        Results:                   Store_Name
        0  Domino's Pizza – Downtown
        ------------------------------
        Step: Analyze a specific user's spending patterns by time of day (e.g., average amount, total amount, and count of transactions per hour).
        Query: SELECT STRFTIME('%H', DateTime) AS Hour_Of_Day, AVG(Amount_EGP) AS Average_Amount, SUM(Amount_EGP) AS Total_Amount, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 GROUP BY Hour_Of_Day ORDER BY Hour_Of_Day;
        Results:   Hour_Of_Day  Average_Amount  Total_Amount  Number_Of_Transactions
        0        None           817.4        122610                     150
        ------------------------------
        Step: Analyze a specific user's spending patterns by day of the week (e.g., average amount, total amount, and count of transactions per day of the week).
        Query: SELECT STRFTIME('%w', DateTime) AS Day_Of_Week_Num, CASE STRFTIME('%w', DateTime) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END AS Day_Of_Week, AVG(Amount_EGP) AS Average_Amount, SUM(Amount_EGP) AS Total_Amount, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 GROUP BY Day_Of_Week_Num ORDER BY Day_Of_Week_Num;
        Results:   Day_Of_Week_Num Day_Of_Week  Average_Amount  Total_Amount  Number_Of_Transactions
        0            None        None           817.4        122610                     150
        ------------------------------
        Step: Analyze a specific user's spending patterns by month (e.g., average amount, total amount, and count of transactions per month).
        Query: SELECT STRFTIME('%Y-%m', DateTime) AS Year_Month, AVG(Amount_EGP) AS Average_Amount, SUM(Amount_EGP) AS Total_Amount, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 GROUP BY Year_Month ORDER BY Year_Month;
        Results:   Year_Month  Average_Amount  Total_Amount  Number_Of_Transactions
        0       None           817.4        122610                     150
        ------------------------------
        Step: Determine the most frequent transaction hour, day of the week, and month for a specific user (mode).
        Query: SELECT (SELECT STRFTIME('%H', DateTime) FROM transactions_table WHERE User_ID = 1 GROUP BY STRFTIME('%H', DateTime) ORDER BY COUNT(*) DESC LIMIT 1) AS Most_Frequent_Hour, (SELECT CASE STRFTIME('%w', DateTime) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END FROM transactions_table WHERE User_ID = 1 GROUP BY STRFTIME('%w', DateTime) ORDER BY COUNT(*) DESC LIMIT 1) AS Most_Frequent_Day_Of_Week, (SELECT STRFTIME('%Y-%m', DateTime) FROM transactions_table WHERE User_ID = 1 GROUP BY STRFTIME('%Y-%m', DateTime) ORDER BY COUNT(*) DESC LIMIT 1) AS Most_Frequent_Month;
        Results:   Most_Frequent_Hour Most_Frequent_Day_Of_Week Most_Frequent_Month
        0               None                      None                None
        ------------------------------
        Step: Identify the categories where a specific user spends most during specific times (e.g., top categories during evening hours).
        Query: SELECT Category, SUM(Amount_EGP) AS Total_Amount_Spent, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 AND STRFTIME('%H', DateTime) BETWEEN '18' AND '23' GROUP BY Category ORDER BY Total_Amount_Spent DESC;
        Results: Empty DataFrame
        Columns: [Category, Total_Amount_Spent, Number_Of_Transactions]
        Index: []
        ------------------------------
        Step: Identify the locations (City and Neighborhood) where a specific user spends most during specific times (e.g., top locations on weekends).
        Query: SELECT City, Neighborhood, SUM(Amount_EGP) AS Total_Amount_Spent, COUNT(Transaction_ID) AS Number_Of_Transactions FROM transactions_table WHERE User_ID = 1 AND STRFTIME('%w', DateTime) IN ('0', '6') GROUP BY City, Neighborhood ORDER BY Total_Amount_Spent DESC;
        Results: Empty DataFrame
        Columns: [City, Neighborhood, Total_Amount_Spent, Number_Of_Transactions]
        Index: []
        ------------------------------
        Step: Determine the average spending per category per month for a specific user.
        Query: SELECT STRFTIME('%Y-%m', DateTime) AS Year_Month, Category, AVG(Amount_EGP) AS Average_Spending FROM transactions_table WHERE User_ID = 1 GROUP BY Year_Month, Category ORDER BY Year_Month, Category;
        Results:   Year_Month       Category  Average_Spending
        0       None      Education        125.833333
        1       None  Entertainment        561.911765
        2       None  Food & Dining        164.777778
        3       None         Health        223.750000
        4       None       Shopping       1725.744681
        5       None         Travel       1571.875000
        ------------------------------
        Step: Determine the average spending per location (City and Neighborhood) per month for a specific user.
        Query: SELECT STRFTIME('%Y-%m', DateTime) AS Year_Month, City, Neighborhood, AVG(Amount_EGP) AS Average_Spending FROM transactions_table WHERE User_ID = 1 GROUP BY Year_Month, City, Neighborhood ORDER BY Year_Month, City, Neighborhood;
        Results:   Year_Month                 City                 Neighborhood  Average_Spending
        0       None  6th of October City               Mall of Arabia        133.333333
        1       None           Alexandria                  Al Mesallah        141.250000
        2       None                Cairo  Cairo International Airport       3002.500000
        3       None                Cairo                     Downtown        208.666667
        4       None                Cairo                   Heliopolis       2356.428571
        5       None                Cairo                    Nasr City       2073.571429
        6       None                Cairo                       Ramses        171.000000
        7       None                Cairo                      Zamalek         90.000000
        8       None                 Giza             Giza (CU Campus)        120.000000
        9       None               Online                       Online        891.271186
        ------------------------------
        Step: Show user personal data like Name, Age, Gender, and Job_Title.
        Query: SELECT Name, Age, Gender, Job_Title FROM user_table WHERE ID = 1;
        Results:            Name  Age Gender Job_Title
        0  Ahmed Hassan   24   Male   Student
    """
    final_state = presentation_super_agent.invoke({"insights": insights, "final_work": "nothing done till now", "send_by":"User","message": "Hello, pls understand the insights given"})
    with open("outdata/presentation_super_agent_output.html", "w") as f:
        f.write(final_state["final_work"])
    # ======================================================================

    ## behavior analyst agent output
    # final_state = behaviour_analyst_super_agent.invoke({})
    # returned = final_state["returned"].output
    # returned = ast.literal_eval(returned)
    # for step in returned:
    #     print("Step:", step)
    ##======================================================================
    
    
    ## database agent output
    # request = """   Step: Retrieve the total spending and the total number of transactions for a specific user.
    #                 Step: Calculate the mean, median, minimum, and maximum transaction amounts for a specific user.
    #                 Step: Determine the mode of transaction amount for a specific user.
    #                 Step: Identify the top spending categories for a specific user, including the total amount spent and the number of transactions in each category.
    #                 Step: Calculate the mean, median, minimum, and maximum transaction amounts for each spending category for a specific user.
    #                 Step: Find the most frequent spending category (mode) for a specific user.
    #                 Step: Identify the top locations (City and Neighborhood) where a specific user spends, including total amount and transaction count for each location.
    #                 Step: Calculate the mean, median, minimum, and maximum transaction amounts for each City and Neighborhood for a specific user.
    #                 Step: Find the most frequent spending location (mode of Neighborhood and City) for a specific user.
    #                 Step: Identify the top stores where a specific user spends, including total amount and transaction count for each store.
    #                 Step: Calculate the mean, median, minimum, and maximum transaction amounts for each store for a specific user.
    #                 Step: Find the most frequent store (mode) for a specific user.
    #                 Step: Analyze a specific user's spending patterns by time of day (e.g., average amount, total amount, and count of transactions per hour).
    #                 Step: Analyze a specific user's spending patterns by day of the week (e.g., average amount, total amount, and count of transactions per day of the week).
    #                 Step: Analyze a specific user's spending patterns by month (e.g., average amount, total amount, and count of transactions per month).
    #                 Step: Determine the most frequent transaction hour, day of the week, and month for a specific user (mode).
    #                 Step: Identify the categories where a specific user spends most during specific times (e.g., top categories during evening hours).
    #                 Step: Identify the locations (City and Neighborhood) where a specific user spends most during specific times (e.g., top locations on weekends).
    #                 Step: Determine the average spending per category per month for a specific user.
    #                 Step: Determine the average spending per location (City and Neighborhood) per month for a specific user.
    #                 Step: Show user personal data like Name, Age, Gender, and Job_Title.
    #             """
    # out = database_agent_super_agent.invoke({"request":request})
    # print(out['output'])
    
    # j = json.loads(out['output'])['final_output']
    # for step in j:
    #     print("-"*30)
    #     print("Step:", step['step'])
    #     print("Query:", step['query'])
    # print("-"*30)
    ##======================================================================

if __name__ == "__main__":
    main()