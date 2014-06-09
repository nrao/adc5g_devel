# Introduction

The Roach 2 boards used for Vegas and DIBAS each have two ADC cards.  On the time scale of a few times a year, these cards need to be calibrated.  In addition, whenever the boards are power cycled, the calibration results need to be reloaded.

This document describes the AdcCalibration code, which performs the above tasks.

# Background

   * This code is based off Hong Chen's version of Jack Hickish's code: https://github.com/jack-h/adc_tests
   * See Hong Chen's usage notes of the original code: ADC5GNotes.pdf
   * See the data sheet on this device: Ev8aq160.pdf
   * See this wiki page for more details: https://safe.nrao.edu/wiki/bin/view/GB/Software/VegasADCCalibration

# Glossary

   * MMCM - Is the "mixed mode clock manager".  This is used for correcting the phase of the capture clock between the four cores.  Depending on where the rising edge of the capture clock lies, glitches in the ADC samples can occur.  The ADC has the ability to provide test ramps that they use to detect glitches and adjust the MMCM appropriately to eliminate them.  One must eliminate the glitches before applying the ogp & inl corrections (see below).

   * OGP - Offset, Gain, Phase.  The offset correction really takes care of 95% of the ADC calibration.
   * INL - Integral Non Linearity.
   * SPI -  The Serial Peripheral Interface or SPI bus is a synchronous serial data link, a de facto standard, named by Motorola, that operates in full duplex mode. It is used for short distance, single master communication, for example in embedded systems, sensors, and SD cards.
   * zdok - 0 or 1. Basically refers to one of the two ADC cards.

# Details

## Files and Classes:

   * _adc\_calibration.py_:  This is the main entry point for program that calibrates the cards.
   * _adc\_load\_calibration.py_: This is the main entry point for reloading calibration results from files.
   * _adc\_read\_only\_check.py_: This is an entry point for simply taking snapshots of the ADC data.
   * _adc\_cal\_logging.conf_: This is the configuration file used by the logger for this software package.
   * _ADCCalibrate.py_: The ADCCalibrate class the main top-level class used by the two entry points ('main's) described above.  It in turn uses a suite of helper classes (see below) to perform the actual calibration.  It may interact with the user.
   * _MMCM.py_: This is a mid-level class that is responsible for performing the MMCM calibration.  It does not directly interact with hardware.
   * _OGP.py_: This is a mid-level class responsible for obtaining and/or loading the Offset, Gain, and Phase measurements.  It does not directly interact with hardware.
   * _INL.py_: This is a mid-level class responsible for obtaining and/or loading the Integral Non Linearity measurements.  It does not directly interact with hardware.
   * _SPI.py_: This is a low-level class that is responsible for communicating with the ADC cards via the FPGA's 'adc5g_controller' pseudo-register.  It *does* interact directly with hardware.
   * _AdcSnapshot.py_ : This is a low-level class responsible for taking 'snapshot's of the ADC data via the FPGA.  It *does* interact directly with hardware.
   * _GPIB.py_: This is a low-level class responsible for communicating with a synthesizer via gpib for setting only frequency and amplitude.  It *does* interact directly with hardware.

## Output Files

The calibration code produces a lot of output files.  Some are just of intermediate in nature and can probably be ignored.  There are two main types:

   * plot .png files: these have filenames that match the pattern [title]_[roach]_z[zdoks]_[timestamp].png, where zdoks can be 0,1, or 2 for *both* zdoks.
   * data files: these have filenames that match the patter [tittle]_[roach]_z[zdok]_[timestamp].[ext], where zdok is always either just 0 or 1.  Title can be in the set (ogp, inl, snapshot_raw).

Heres a listing of some of the important data files:

   * ogp_[roach]_z[zdok]_[timestamp] : these hold the calibration results for the OGP.  This is one of the calibration files that get loaded.
   * inl_[roach]_z[zdok]_[timestamp].meas : these hold the calibration results for the INL.  This is one of the calibration files that get loaded.
   * inl_[roach]_z[zdok]_[timestamp] : TBF - what is this file for?
   * snapshot_raw_[roach]_z[zdok]_[timestamp].dat* - TBF

Here's some of the important plot files:

   * post_adjustment_test_[freq]MHz_[roach]_z[zdoks]_[timestamp].png - this spectral line plot is produced after changes in [freq] when adc_calibration.py promts for new frequencies to test (after calibrations).
   * post_mmcm_ramp_check_[roach]_z[zdoks]_[timestamp].png - a raw data plot done after the MMCM calibration phase. 
   * raw_startup_[roach]_z[zdoks]_[timestamp].png - a raw data plot done before calibrations are completed.

