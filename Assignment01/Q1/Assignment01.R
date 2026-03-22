library(tidyverse)
library(dplyr)
library(car)

# Import “airplane price data set” to R.
# The data set consists of following variables: Model, Production Year, Number of 
# Engines, Engine Type, Capacity, Range (km), Fuel Consumption, Hourly Maintenance, 
# age, Sales Region and Price of different airplanes.


# ------------------------------------------ A ------------------------------------------
# Import data set into R, assigning the type of each variable correctly.
# ---------------------------------------------------------------------------------------

air_data <- read.csv("airplane_price_dataset.csv", sep=",", stringsAsFactors=TRUE)
air_data <- air_data |>
  rename(
    FC = FuelConsumption.L.h.,
    HM = HourlyMaintenance...,
    Price = Price...
  )
air_data$EngineType <- as.factor(air_data$EngineType)

str(air_data)


# ------------------------------------------ B ------------------------------------------
# Summarize the variables Price, Fuel Consumption first for the all data and then
# for the groups of Engine Type.
# ---------------------------------------------------------------------------------------

air_data[, c("Price", "FC")] |>
  summarize(
    Mean_Price = mean(Price, na.rm = TRUE),
    Median_Price = median(Price, na.rm = TRUE),
    SD_Price = sd(Price, na.rm = TRUE),
    Mean_Fuel = mean(FC, na.rm = TRUE),
    Median_Fuel = median(FC, na.rm = TRUE),
    SD_Fuel = sd(FC, na.rm = TRUE)
  )

par(mfrow = c(1,2)) # layout 2 charts in 1 row
hist(air_data$Price, 
     main = "Histogram of Price", 
     xlab = "Price", 
     col = "lightblue")
# plot(density(air_data$Price), )
hist(air_data$FC, 
     main = "Histogram of Fuel Consumption", 
     xlab = "Fuel Consumption (L/h)", 
     col = "lightgreen")
# plot(density(air_data$FC))
par(mfrow = c(1,1))


divided_data = split(air_data, air_data$EngineType)
Turbofan_data <- divided_data[[1]]
Piston_data <- divided_data[[2]]


par(mfrow = c(2,2)) # Layout 4 charts in a 2x2 grid
# Price Histograms
hist(Piston_data$Price,
     main = "Piston: Price", 
     xlab = "Price",
     col = "lightblue")
hist(Turbofan_data$Price,
     main = "Turbofan: Price", 
     xlab = "Price",
     col = "lightblue")

# Fuel Consumption Histograms
hist(Piston_data$FC,
     main = "Piston: Fuel Consumption", 
     xlab = "Fuel Consumption",
     col = "lightgreen")
hist(Turbofan_data$FC,
     main = "Turbofan: Fuel Consumption", 
     xlab = "Fuel Consumption",
     col = "lightgreen")
par(mfrow = c(1,1)) 

# plot(density(air_data$Price), xlim = range(0, 70), ylim = range(0, 0.1))
# lines(density(Turbofan_data$Price), col=2)
# lines(density(Piston_data$Price), col=3)

# Calculate densities first to find the correct x and y limits
dens_turbo <- density(Turbofan_data$FC, na.rm = TRUE)
dens_piston <- density(Piston_data$FC, na.rm = TRUE)

plot(dens_turbo, col = "red",
     main = "Density of Fuel Consumption by Engine Type",
     xlab = "Fuel Consumption",
     xlim = range(c(dens_turbo$x, dens_piston$x)), 
     ylim = range(c(dens_turbo$y, dens_piston$y)))
lines(dens_piston, col = "blue")
legend("topright", legend = levels(air_data$EngineType), col = c("blue", "red"), lty = 1)


# ------------------------------------------ C ------------------------------------------
# Test whether Fuel Consumption is affected from the Engine Type of the plane. Check the
# assumptions and visualize the relationship between these two characteristics.
# ---------------------------------------------------------------------------------------

# Boxplot is best for comparing a continuous variable across categories
boxplot(FC ~ EngineType, data = air_data,
        main = "Fuel Consumption by Engine Type",
        xlab = "Engine Type", ylab = "Fuel Consumption",
        col="lightgreen")

# Normality test
shapiro.test(Turbofan_data$FC)
shapiro.test(Piston_data$FC) # Error, data size > 5000
# Variance test
leveneTest(FC ~ EngineType, data = air_data)

t.test(FC ~ EngineType, data = air_data)

# p-value < 2.2e-16, alternative hypothesis: true difference in means between group 
# Piston and group Turbofan is not equal to 0
# 95 percent confidence interval:
#  21.09784 22.11459


# ------------------------------------------ D ------------------------------------------
# Construct 95% confidence intervals for the mean of two groups and interpret them.
# ---------------------------------------------------------------------------------------

# 95% Confidence Intervals for the mean of each group
cat("\n95% CI for Turbofan Fuel Consumption:\n")
t.test(Turbofan_data$FC)$conf.int
cat("\n95% CI for Piston Fuel Consumption:\n")
t.test(Piston_data$FC)$conf.int


# ------------------------------------------ E ------------------------------------------
# Check the association between Model and Sales Region in the whole sample using proper
# method and interpret your findings.
# ---------------------------------------------------------------------------------------

# Association between two categorical variables (Chi-Square)
table_model_region <- table(air_data$Model, air_data$SalesRegion)
chisq_result <- chisq.test(table_model_region)
print(chisq_result)
# If the p-value is less than 0.05, you reject the null hypothesis and conclude 
# there is a significant association between the airplane Model and the Sales Region.
# p-value = 0.7 so no association.


# ------------------------------------------ F ------------------------------------------
# Filter your data only considering Bombardier CRJ200 and Cessna 172 model airplanes.
# ---------------------------------------------------------------------------------------

filtered_air_data <- air_data |>
  filter(Model %in% c("Bombardier CRJ200", "Cessna 172")) |>
  droplevels()
  
filtered_air_data  |>
summarize(
  Mean_Price = mean(Price, na.rm = TRUE),
  Median_Price = median(Price, na.rm = TRUE),
  SD_Price = sd(Price, na.rm = TRUE),
  Mean_Fuel = mean(FC, na.rm = TRUE),
  Median_Fuel = median(FC, na.rm = TRUE),
  SD_Fuel = sd(FC, na.rm = TRUE)
)


# ------------------------------------------ G ------------------------------------------
# Check the distribution of Price across two categories of Engine type. (You can apply
# transformation if you think it is required)
# ---------------------------------------------------------------------------------------

# Plotting Log-transformed Price to normalize the distribution
boxplot(log(Price) ~ EngineType, data = filtered_air_data, 
        main = "Log Transformed Price by Engine Type", 
        xlab = "Engine Type", ylab = "Log(Price)",
        col = "lightgreen")


# ------------------------------------------ H ------------------------------------------
# Categorize the variable Price into two categories as “Low” and “High” by cutting from the
# median and save it as a new variable into your data frame.
# ---------------------------------------------------------------------------------------

median_price <- median(filtered_air_data$Price, na.rm = TRUE)
# Create the new categorical variable "Price_Category"
filtered_air_data$Price_Category <- factor(
  ifelse(filtered_air_data$Price > median_price, "High", "Low")
)

str(filtered_air_data$Price_Category)


# ------------------------------------------ I ------------------------------------------
# Cross classify model and price categories and interpret the conditional probabilities.
# ---------------------------------------------------------------------------------------

# Cross classify model and price categories
cross_model_price <- table(filtered_air_data$Model, filtered_air_data$Price_Category)

cat("\nCross Classification Table (Counts):\n")
print(cross_model_price)
cat("\nConditional Probabilities (Row proportions):\n")
print(prop.table(cross_model_price, margin = 1))

# Interpretation: Shows the probability of an airplane having a "High" or "Low" price GIVEN its specific Model.


# ------------------------------------------ J ------------------------------------------
# Is there an association between the model of the airplane and its price level.
# Analyze it by using proper statistical method.
# ---------------------------------------------------------------------------------------

# Test association between Model and Price Level using Chi-Square
test_model_price <- chisq.test(cross_model_price)
print(test_model_price)

# Check the assumption: Expected frequencies should be at least 5 in all cells
#cat("\nExpected Frequencies:\n")
#print(test_model_price$expected)

# Interpretation: p-value < 0.05, so there is a significant association between
# the airplane model and its price level.


# ------------------------------------------ K ------------------------------------------
# Cross classify the variables Model and Sales region. Interpret the conditional probabilities
# and then test whether there is an association between these two characteristics.
# ---------------------------------------------------------------------------------------

cat("\nCross Classification - Model and Sales Region:\n")
cross_model_region <- table(filtered_air_data$Model, filtered_air_data$SalesRegion)
print(cross_model_region)

cat("\nConditional Probabilities (Row proportions):\n")
print(prop.table(cross_model_region, margin = 1))

# Interpretation: Shows the probability of an airplane being sold in a specific 
# region GIVEN its Model.

# Test for association
test_model_region <- chisq.test(cross_model_region)
print(test_model_region)
print(test_model_region$residuals)

# Interpretation: p-value = 0.2895, no significant association
# (Note: If you get a warning that expected counts are too low, you might need to use fisher.test(cross_model_region) instead).