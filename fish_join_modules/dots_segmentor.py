import os

from ij import IJ, WindowManager
from ij.plugin import ChannelSplitter


class RSFISHSegmentor:
    """
    Segment dots using the RS-FISH plugin
    """
    _default_params = {
        "mode": "Advanced",
        "anisotropy": 1.0,
        "robust_fitting": "[RANSAC]",
        "compute_min/max": True,
        "use_anisotropy": True,
        "spot_intensity": "[Linear Interpolation]",
        "sigma": 1.4310,
        "threshold": 0.00219,
        "support": 3,
        "min_inlier_ratio": 0.10,
        "max_error": 1.5,
        "spot_intensity_threshold": 3094.59,
        "background": "[No background subtraction]",
        "background_subtraction_max_error": 0.05,
        "background_subtraction_min_inlier_ratio": 0.10,
        "use_multithreading": True,
        "num_threads": 10,
        "block_size_x": 128,
        "block_size_y": 128,
        "block_size_z": 16,
    }

    def __init__(self, channels, result_file_pattern="{image_dir}/{image_title}_C{channel}.csv", params_override={}):
        """
        :param iterable channels: image channels that contain dots information (one-based)
        :param str result_file_pattern: str.format() pattern to determine the path of the output csv.
                                        Can use these placeholders: image_dir, image_title, channel
        :param dict[int, dict] params_override: a dict of per-channel overrides to RS-FISH parameters.
                                                Values should be a dictionary of parameters and their
                                                values (int, float, string, bool). See also default_params().
        """
        self.channels = channels
        self.result_file_pattern = result_file_pattern

        self.params = {}
        for ch in self.channels:
            self.params[ch] = self._default_params.copy()
            # Key in params_override can be a string
            if ch in params_override or str(ch) in params_override:
                ch_override = params_override.get(ch, str(ch))
                self.params[ch].update(ch_override)

    def process_image(self, file_path):
        """
        Run RS-FISH on all requested channels of the image in the given path. Each channel will be run
        with the parameters given during initialization. The resulting dots will be saved to CSV files,
        one per channel. The output file and location are determined using the result_file_pattern attribute.

        :param str file_path: Path to image file
        :return list[str]: Paths of resulting CSV file, one per channel 
        """
        image_dir = os.path.dirname(file_path)
        IJ.log("RSFISHSegmentor: opening image: " + file_path)
        imp = IJ.openImage(file_path)
        image_title = imp.getShortTitle()
        IJ.log("RSFISHSegmentor: {}: splitting to channels".format(image_title))
        imp_channels = ChannelSplitter.split(imp)
        IJ.log("RSFISHSegmentor: {}: image has {} channels, will use {}".format(image_title, len(imp_channels), self.channels))

        output_filenames = []
        for ch in self.channels:
            IJ.log("RSFISHSegmentor: {}: processing channel {}".format(image_title, ch))
            imp_ch = imp_channels[ch-1]
            params_ch = self.params[ch]
            result_file_path = self.result_file_pattern.format(image_dir=image_dir, image_title=image_title, channel=ch)
            IJ.log("RSFISHSegmentor: {}: channel {}: saving to {}".format(image_title, ch, result_file_path))
            self.process_channel(imp_ch, result_file_path, params_ch)
            output_filenames.append(result_file_path)
        rt = WindowManager.getWindow('smFISH localizations')
        if rt:
            rt.close()
        IJ.log("RSFISHSegmentor: {}: done".format(image_title))

        return output_filenames
        
    def process_channel(self, imp, results_file, params):
        """
        Run RS-FISH on a single-channel image and write the results to a file. This is usually run
        via process_image().

        :param ImagePlus imp: ImagePlus object with a single channel
        :param str results_file: Path to output CSV file
        :param dict params: Dictionary of RS-FISH parameters
        """
        params['results_file'] = [results_file]
        params_str = self._create_param_string(params)

        imp.show()
        IJ.run(imp, "RS-FISH", params_str)
        imp.hide()

    def default_params(self):
        """
        Return the default parameters passed to RS-FISH. Mostly useful for reference of available paramerters.
        """
        return self._default_params

    def _create_param_string(self, params):
        param_str = ''
        for key, value in params.items():
            if type(value) is bool and value:
                param_str += '{} '.format(key)
            elif type(value) in [list, tuple]:
                assert len(value) == 1 # The list is to mark that this is a string with spaces, not to hold several values
                param_str += '{}=[{}] '.format(key, value[0])
            elif type(value) is float:
                param_str += '{}={:.4f} '.format(key, value)
            else:
                param_str += '{}={} '.format(key, value)

        return param_str.strip()
