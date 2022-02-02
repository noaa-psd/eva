# (C) Copyright 2021-2022 United States Government as represented by the Administrator of the
# National Aeronautics and Space Administration. All Rights Reserved.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.


# --------------------------------------------------------------------------------------------------


from eva.base import Base
from eva.utilities import ioda_definitions
from eva.utilities import ioda_netcdf_api
from eva.plot_tools.scatter_correlation import scatter_correlation_plot

import netCDF4
import numpy as np
import os


# --------------------------------------------------------------------------------------------------


# TODO: needs to be ioda-erized and r2d2-erized

class ObsCorrelationScatter(Base):

    def execute(self):

        # Make copy of config
        # -------------------
        config = self.config

        # Parse configuration
        # -------------------
        # Platforms to plot
        platforms = config.get("platforms")

        # Files containing experiment hofx files
        ioda_exp_file_template = config.get("ioda experiment files")
        ioda_ref_file_template = config.get("ioda reference files")

        # Get metrics to plot
        comparisons = config.get("comparisons")

        # Marker size for scatter
        marker_size = config.get("marker size", 2)

        # Output path
        output_path = config.get("output path", "./")

        # Figure file type (pdf, png, etc)
        file_type = config.get("figure file type", "png")

        # Loop over hofx files
        # --------------------
        for platform in platforms:

            # In a standalone mode it user can template the files with platform to allow looping
            ioda_exp_file = ioda_exp_file_template.replace("PLATFORM", platform)
            ioda_ref_file = ioda_ref_file_template.replace("PLATFORM", platform)

            # Message files being read
            self.logger.info(" Experiment file: "+ioda_exp_file)
            self.logger.info(" Reference file:  "+ioda_ref_file)

            # Output filename
            pathfile = os.path.split(ioda_exp_file)
            source_file = pathfile[1]

            # Get platform name
            platform_long_name = ioda_definitions.ioda_platform_to_full_name(platform, self.logger)

            # Open the file
            fh_exp = netCDF4.Dataset(ioda_exp_file)
            fh_ref = netCDF4.Dataset(ioda_ref_file)

            # Get potential variables
            variables = fh_exp.groups['hofx'].variables.keys()

            # Check for channels
            try:
                number_channels = fh_exp.dimensions["nchans"].size
                has_chan = True
            except Exception:
                number_channels = 1
                has_chan = False

            # Check for similarity of channels
            if has_chan:
                channels_exp = fh_exp.variables['nchans'][:]
                channels_ref = fh_ref.variables['nchans'][:]
                assert not any(channels_exp != channels_ref), "Files being have different channels"

            # Loop over metrics
            # -----------------
            for comparison in comparisons:

                exp_metric = comparison[0]
                ref_metric = comparison[1]

                self.logger.info(" ")
                self.logger.info("  Comparison: "+exp_metric+" versus "+ref_metric)

                # Long names for metrics
                exp_metric_long_name = ioda_definitions.ioda_group_dict(exp_metric, self.logger)
                ref_metric_long_name = ioda_definitions.ioda_group_dict(ref_metric, self.logger)

                # Loop over variables
                # -------------------
                for variable in variables:

                    variable_name = variable
                    variable_name_no_ = variable.replace("_", " ")
                    variable_name_no_ = variable_name_no_.capitalize()
                    variable_name_no_fix = variable_name_no_

                    # Loop over channels
                    # -------------------
                    for channel_idx in range(number_channels):

                        # Read the data
                        # -------------
                        if has_chan:

                            channel = channels_exp[channel_idx]

                            # Add channel number to name
                            variable_name = variable + "-channel_" + str(channel)
                            variable_name_no_ = variable_name_no_fix + " channel " + str(channel)

                            self.logger.info("    Variable: " + variable_name_no_ +
                                             " (of " + str(number_channels) + ")")

                            data_exp = ioda_netcdf_api.read_ioda_variable(fh_exp, exp_metric,
                                                                          variable, channel_idx)
                            data_ref = ioda_netcdf_api.read_ioda_variable(fh_ref, ref_metric,
                                                                          variable, channel_idx)

                        else:

                            self.logger.info("    Variable: "+variable_name_no_+"")

                            data_exp = ioda_netcdf_api.read_ioda_variable(fh_exp, exp_metric,
                                                                          variable)
                            data_ref = ioda_netcdf_api.read_ioda_variable(fh_ref, ref_metric,
                                                                          variable)

                        # Remove missing values (<-10e10)
                        # -------------------------------
                        remove_idx_exp = np.where(data_exp < -10e10)[0]
                        remove_idx_ref = np.where(data_ref < -10e10)[0]
                        remove_idx = np.unique(np.concatenate([remove_idx_exp, remove_idx_ref]))

                        make_plot = True
                        if len(remove_idx) > 0:
                            self.logger.info('      Missing values: removing ' + len(remove_idx) +
                                             ' values. Original number of locations:' +
                                             len(data_exp))
                            if (len(remove_idx) != len(data_exp)):
                                data_exp = np.delete(data_exp, remove_idx)
                                data_ref = np.delete(data_ref, remove_idx)
                            else:
                                make_plot = False
                                self.logger.info('      No data for this variable/channel, ' +
                                                 'skip plotting')

                        # Create and save the figure
                        # --------------------------
                        if make_plot:

                            # Create output filename
                            output_path_fig = os.path.join(output_path, platform, variable_name)
                            os.makedirs(output_path_fig, exist_ok=True)
                            output_file = platform+'-'+exp_metric+'_vs_'+ref_metric+'.'+file_type
                            output_file = os.path.join(output_path_fig, output_file)

                            # Title for the plot
                            plot_title = platform_long_name + ' | ' + variable_name_no_

                            # Create the plot
                            scatter_correlation_plot(data_ref, data_exp, ref_metric_long_name,
                                                     exp_metric_long_name, plot_title, output_file,
                                                     marker_size=marker_size)

            # Close files
            fh_exp.close()
            fh_ref.close()
            self.logger.info(" ")