library(feather)
library(ggeffects)

df <- read_feather('DATA\\final.feather')

weather <- c('cut', 'wind', 'precipitation', 'temp', 'pressure')
subs <- c('CO', 'NO2', 'PM10', 'PM25', 'SO2')

for (sub in subs){
  sts <- names(df)[grep(sub, names(df))][-1]
  a <- paste(sts, collapse=' + ')
  b <- paste(weather, collapse = ' + ')
  right <- paste(c(a, b), collapse= ' + ')
  formula <- paste(sub, " ~ ", right)
  mod <- lm(as.formula(formula), data=df)
  path <- paste(c("REGRESSIONS\\", sub, "_reg.txt"), collapse='', sep='')
  capture.output(summary(mod), file = path)
  tab <- ggemmeans(mod, terms='cut')
  tab$var <- sub
  path <- paste(c("REGRESSIONS\\", sub, "_gg.csv"), collapse='', sep='')
  write.csv(tab, path)
}
