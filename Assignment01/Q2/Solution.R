library(tidyverse)
library(car)
library(lmtest)

# Import “airplane price data set” to R.
# The data set consists of following variables: Model, Production Year, Number of 
# Engines, Engine Type, Capacity, Range (km), Fuel Consumption, Hourly Maintenance, 
# age, Sales Region and Price of different airplanes.


# ------------------------------------------ A ------------------------------------------
# Create a new data frame only including “Airbus A320”, “Airbus A350”, “Boeing 737” and
# “Boeing 777” models of airplanes. Checked the distribution of Price first for the observations
# in this sample and then for each model in the data frame. Interpret your findings.
# ---------------------------------------------------------------------------------------

air_data <- read.csv("../data/airplane_price_dataset.csv", sep=",", stringsAsFactors=TRUE)
air_data <- air_data |>
  filter(Model %in% c("Airbus A320", "Airbus A350", "Boeing 737", "Boeing 777")) |>
  droplevels()
air_data <- air_data |>
  rename(
    FC = FuelConsumption.L.h.,
    HM = HourlyMaintenance...,
    RangeKm = Range.km.,
    Price = Price...
  )
air_data$EngineType <- as.factor(air_data$EngineType)
# Price is generally right-skewed data; a log() transformation helps to normalize the data
air_data$Price <- log(air_data$Price)

str(air_data)

hist(air_data$Price, 
     main = "Histogram of Price (Models: Airbus A320, Airbus A350, Boeing 737, Boeing 777)", 
     xlab = "Price", 
     col = "lightblue")

densityA320 <- density(air_data$Price[air_data$Model == "Airbus A320"], na.rm = TRUE)
densityA350 <- density(air_data$Price[air_data$Model == "Airbus A350"], na.rm = TRUE)
densityB737 <- density(air_data$Price[air_data$Model == "Boeing 737"], na.rm = TRUE)
densityB777 <- density(air_data$Price[air_data$Model == "Boeing 777"], na.rm = TRUE)

plot(densityA320, col = "red",
     main = "Price by Model",
     xlab = "Price",
     xlim = range(c(densityA320$x, densityA350$x, densityB737$x, densityB777$x)),
     ylim = range(c(densityA320$y, densityA350$y, densityB737$y, densityB777$y)))
lines(densityA350, col = "blue")
lines(densityB737, col = "green")
lines(densityB777, col = "purple")
legend("topright", legend = levels(air_data$Model), col = c("red", "blue", "green", "purple"), lty = 1)


# ------------------------------------------ B ------------------------------------------
# Analyze the numerical variables that are affected by the “Model”. Test the assumptions of
# the statistical method, for the cases that you have found a significant association, by using
# corresponding tests and plots. Write your conclusions. 
# ---------------------------------------------------------------------------------------

str(air_data)

# Numerical vars only
num_vars <- names(air_data)[sapply(air_data, is.numeric)]
par(mfrow = c(3, 3))
for (var in num_vars) {
  boxplot(air_data[[var]] ~ air_data$Model,
          main = paste(var, "by Model"),
          xlab = "Model", 
          ylab = var,
          col = "lightgreen")
}
par(mfrow = c(1, 1))

# Based on the boxplots, variables **Price**, **Capacity**, and **RangeKm** are the ones affected by Model.

# ANOVA and analysis
aov_price <- aov(Price ~ Model, data = air_data)
aov_capacity <- aov(Capacity ~ Model, data = air_data)
aov_range <- aov(RangeKm ~ Model, data = air_data)
summary(aov_price)

# Assumptions of ANOVA
# Populations from which the samples are selected must be normal
par(mfrow = c(1, 3))
qqnorm(aov_price$residuals, main = "Price Q-Q Plot")
qqnorm(aov_capacity$residuals, main = "Capacity Q-Q Plot")
qqnorm(aov_range$residuals, main = "RangeKm Q-Q Plot")
par(mfrow = c(1, 1))
#shapiro.test(residuals(aov_price))

# Observations within each sample must be independent
dwtest(aov_price, alternative ="two.sided")

# Kolmogorov-Smirnov Test ???
# ks.test(residuals(aov_price), "pnorm", mean(residuals(aov_price)), sd(residuals(aov_price)))
# Populations from which the samples are selected must have equal variances (homogeneity of variance)
bptest(aov_price)


# ------------------------------------------ C ------------------------------------------
# Apply a two-way ANOVA including Sales Region to the model. Interpret your findings.
# ---------------------------------------------------------------------------------------

# Two-Way ANOVA and analysis
aov2_price <- aov(Price ~ Model * SalesRegion, data = air_data)
summary(aov2_price)
aov2_capacity <- aov(Capacity ~ Model * SalesRegion, data = air_data)
summary(aov2_capacity)
aov2_range <- aov(RangeKm ~ Model * SalesRegion, data = air_data)
summary(aov2_range)

# Region does not seem to influence any of the 3 numeric variables affected by Model


# ------------------------------------------ D ------------------------------------------
# Convert the variable Production Year to a categorical variable with two levels as “Older” and
# “Newer” and save it as a new variable named “year_cat” in the data frame.
# ---------------------------------------------------------------------------------------

cutoff = median(air_data$ProductionYear)
air_data$year_cat <- as.factor(ifelse(air_data$ProductionYear < cutoff, "Older", "Newer"))
str(air_data)


# ------------------------------------------ E ------------------------------------------
# Analyze the effect of Model and year (“year_cat”) together on the price. Analyze whether the
# interaction of two term is significant. Interpret your findings.
# ---------------------------------------------------------------------------------------

# Two-Way ANOVA and analysis
aov2_price <- aov(Price ~ Model * year_cat, data = air_data)
summary(aov2_price)

# Test normality assumption for Two-Way ANOVA
qqnorm(aov2_price$residuals)
shapiro.test(residuals(aov2_price))

# Observations within each sample must be independent
dwtest(aov2_price, alternative ="two.sided")

# Kolmogorov-Smirnov Test ???
ks.test(residuals(aov2_price), "pnorm", mean(residuals(aov2_price)), sd(residuals(aov2_price)))
# Populations from which the samples are selected must have equal variances (homogeneity of variance)
bptest(aov2_price)



