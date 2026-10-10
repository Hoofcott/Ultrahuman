[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/anant)
# Ultrahuman Ring

This integration uses the official Ultrahuman Vision API to retrieve Ultrahuman AIR Ring information periodically and expose it in HomeAssistant through various sensors.

## HOW TO USE
1. Download repository via HACS store
2. Go to Integrations -> Add Integration -> Ultrahuman Ring
3. Enter API-KEY (see below for steps)
4. Integration should be fully configured now and a few sensor entities will be available for use in HomeAssistant. 

## Obtaining API-Key
1. Visit https://vision.ultrahuman.com/developer
2. Log in
3. Click on "Personal API Tokens" and then "Generate New Token"
4. Enter any suitable name for token name (ex: "YourName Ultrahuman Air Token")
5. (OPTIONAL) Set token expiry to 10 years
6. Select RING DATA ACCESS checkbox
7. Click Generate Token
8. Copy token as this will be required during integration onboarding

## Sensors (fork Hoofcott, v1.2.0)
Cardio: Heart Rate, Night Resting HR, HRV (sleep average), HRV Day Average, Sleep RHR, SpO2, VO2 Max.
Sleep: Sleep Score (contributors as attributes), Total Sleep, Time in Bed, Sleep Start/End, Deep / REM / Light sleep, Awake Time, Sleep Efficiency, Restorative Sleep, Full Sleep Cycles, Tosses and Turns, Sleep Movements, Morning Alertness.
Activity: Recovery Index, Movement Index, Active Minutes, Weekly Active Minutes, Inactive Time, Steps.
Temperature: Skin Temperature (last sample), Sleep Body Temperature, Temperature Deviation (vs baseline).

Changes vs upstream: SpO2/HR/HRV report `unknown` instead of `0` when the API has no measurement, steps are integers, skin temperature keeps its decimals.

## Notes:
1. This integration only shows data  present on Ultrahuman's servers. Therefore the ring must sync with the mobile app for the latest data.
2. The integration fetches data periodically from Ultrahuman's servers.
3. Ultrahuman's API only returns the metrics available at time of fetch. Due to this sensors will be marked unknown every time that metric is missing from the API response.
(Generally the V02 metric is always available).
4. Please feel free to create a new Issue or Pull Request to introduce any missing sensor entities you would like to see this integration provide.
