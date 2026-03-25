# Q2 Solutions

Import “airplane price data set” into R. The data set consists of following variables: Model, Production Year, Number of Engines, Engine Type, Capacity, Range (km), Fuel Consumption, Hourly Maintenance, age, Sales Region and Price of different airplanes.


## Create a new data frame only including “Airbus A320”, “Airbus A350”, “Boeing 737” and “Boeing 777” models of airplanes. Check the distribution of Price: first for the observations in this sample and then for each model in the data frame. Interpret your findings.

```r
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
```

![summary-price-all](./summary-price-all.png)
*Figure 01*

![summary-price-by-model](./summary-price-by-model.png)
*Figure 02*

 According to the plots, Price looks more normally distributed after applying a log() transformation and also dividing it by model.
 A320 and B737 are the cheaper plane models of each company while A350 and B777 are the more expensive ones.


## Analyze the numerical variables that are affected by the “Model”. Test the assumptions of the statistical method, for the cases that you have found a significant association, by using corresponding tests and plots. Write your conclusions.

```r
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
```

![boxplot-of-numerics](./boxplot-of-numerics.png)
*Figure 03*

Based on the boxplots, variables **Price**, **Capacity**, and **RangeKm** are the ones affected by **Model**. We are selecting those 3 to do further analysis.

#### Assumption analysis

![qqplot-numerical-all](./qqplot-numerical-all.png)
*Figure 04*

According to the QQ-plot, **Price** looks a bit curved with respect to the line meaning it might not be normally distributed.
This could mean that newer plane prices skew the data ?? or that another factor is affecting the data ???

For the case of **Capacity** and **RangeKm**, the QQ-plot show a horizontal flat line, meaning the data is not normally distributed.

In any case ANOVA is not the right test to apply in these cases and further analysis is required.

```r
# ANOVA & Assumptions
aov_price <- aov(Price ~ Model, data = air_data)
summary(aov_price)
# Populations from which the samples are selected must be normal
qqnorm(aov_price$residuals)
shapiro.test(residuals(aov_price))
# Observations within each sample must be independent
dwtest(aov_price, alternative ="two.sided")
# Populations from which the samples are selected must have equal variances (homogeneity of variance)
bptest(aov_price)
```


## Apply a two-way ANOVA including Sales Region to the model. Interpret your findings.

```r
aov2_price <- aov(Price ~ Model * SalesRegion, data = air_data)
summary(aov2_price)
aov2_capacity <- aov(Capacity ~ Model * SalesRegion, data = air_data)
summary(aov2_capacity)
aov2_range <- aov(RangeKm ~ Model * SalesRegion, data = air_data)
summary(aov2_range)
```

**Region** does not seem to influence any of the 3 numeric variables affected by **Model**.


## Convert the variable Production Year to a categorical variable with two levels as “Older” and “Newer” and save it as a new variable named “year_cat” in the data frame.

```r
cutoff = median(air_data$ProductionYear)
air_data$year_cat <- as.factor(ifelse(air_data$ProductionYear < cutoff, "Older", "Newer"))
str(air_data)
```


## Analyze the effect of Model and year (“year_cat”) together on the price. Analyze whether the interaction of two term is significant. Interpret your findings.

![qqplot-price-model-year](./qqplot-price-model-year.png)
*Figure 05*

```r
aov2_price <- aov(Price ~ Model * year_cat, data = air_data)
summary(aov2_price)

# Test normality assumption for Two-Way ANOVA
qqnorm(aov2_price$residuals)
shapiro.test(residuals(aov2_price))
# Observations within each sample must be independent
dwtest(aov2_price, alternative ="two.sided")
# Populations from which the samples are selected must have equal variances (homogeneity of variance)
bptest(aov2_price)
```

Model and year_cat interaction look to adjust to the assumptions, so an ANOVA test could be the right one. 

![anova-price-model-year](./anova-price-model-year.png)
*Figure 06*

According to the output, both Model and year cat do not seem to affect Price.


# iii) Do not forget to do multiple comparisons tests! Apply post hoc tests to see where the differences source from. Apply three different post hoc tests and compare their findings.