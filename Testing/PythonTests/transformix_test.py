# =========================================================================
#
#  Copyright UMC Utrecht and contributors
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0.txt
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
# =========================================================================

"""transformix test module."""

import os
import filecmp
import pathlib
import subprocess
import sys
import unittest
import SimpleITK as sitk
import numpy as np


class TransformixTestCase(unittest.TestCase):
    """Tests transformix from https://elastix.lumc.nl"""

    version_string = "5.0.1"
    transformix_exe_file_path = pathlib.Path(os.environ["TRANSFORMIX_EXE"])
    temporary_directory_path = pathlib.Path(os.environ["TRANSFORMIX_TEST_TEMP_DIR"])

    def get_name_of_current_function(self):
        """Returns the name of the current function"""

        return sys._getframe(1).f_code.co_name

    def create_test_function_output_directory(self):
        """Creates an output directory for the current test function, and returns its path."""

        directory_path = self.temporary_directory_path / sys._getframe(1).f_code.co_name
        directory_path.mkdir(exist_ok=True)
        return directory_path

    def assert_equal_image_info(self, actual: sitk.Image, expected: sitk.Image) -> None:
        """Asserts that the actual image has the same image information (size, spacing, pixel type,
        etc) as the expected image."""

        self.assertEqual(actual.GetDimension(), expected.GetDimension())
        self.assertEqual(actual.GetSize(), expected.GetSize())
        self.assertEqual(actual.GetSpacing(), expected.GetSpacing())
        self.assertEqual(actual.GetOrigin(), expected.GetOrigin())
        self.assertEqual(actual.GetDirection(), expected.GetDirection())
        self.assertEqual(
            actual.GetPixelIDTypeAsString(), expected.GetPixelIDTypeAsString()
        )

    def test_without_arguments(self) -> None:
        """Tests executing transformix without arguments"""

        completed = subprocess.run(
            [str(self.transformix_exe_file_path)], capture_output=True, check=True
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(
            completed.stdout.decode().strip(),
            'Use "transformix --help" for information about transformix-usage.',
        )

    def test_help(self) -> None:
        """Tests --help"""

        completed = subprocess.run(
            [str(self.transformix_exe_file_path), "--help"],
            capture_output=True,
            check=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        self.assertTrue(
            "transformix applies a transform on an input image and/or"
            in completed.stdout.decode()
        )

    def test_version(self) -> None:
        """Tests --version"""

        completed = subprocess.run(
            [str(self.transformix_exe_file_path), "--version"],
            capture_output=True,
            check=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")
        self.assertEqual(
            completed.stdout.decode().strip(),
            "transformix version: " + self.version_string,
        )

    def test_extended_version(self) -> None:
        """Tests --extended-version"""

        completed = subprocess.run(
            [str(self.transformix_exe_file_path), "--extended-version"],
            capture_output=True,
            check=True,
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(completed.stderr, b"")

        output: str = completed.stdout.decode()
        self.assertTrue("transformix version: " in output)
        self.assertTrue("Git revision SHA: " in output)
        self.assertTrue("Git revision date: " in output)
        self.assertTrue("Memory address size: " in output)
        self.assertTrue("CMake version: " in output)
        self.assertTrue("ITK version: " in output)

    def test_missing_tp_commandline_option(self) -> None:
        """Tests missing -tp commandline option"""

        completed = subprocess.run(
            [
                str(self.transformix_exe_file_path),
                "-in",
                "InputImageFile.ext",
                "-out",
                str(self.create_test_function_output_directory()),
            ],
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(
            completed.stderr.decode().strip(),
            'ERROR: No CommandLine option "-tp" given!',
        )

    def test_missing_out_commandline_option(self) -> None:
        """Tests missing -out commandline options"""

        completed = subprocess.run(
            [
                str(self.transformix_exe_file_path),
                "-in",
                "InputImageFile.ext",
                "-tp",
                "TransformParameters.txt",
            ],
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(
            completed.stderr.decode().strip(),
            'ERROR: No CommandLine option "-out" given!',
        )

    def test_missing_input_commandline_option(self) -> None:
        """Tests missing input commandline option"""

        completed = subprocess.run(
            [
                str(self.transformix_exe_file_path),
                "-tp",
                "TransformParameters.txt",
                "-out",
                str(self.create_test_function_output_directory()),
            ],
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(
            completed.stderr.decode().strip(),
            'ERROR: At least one of the CommandLine options "-in", "-def", "-jac", or "-jacmat" should be given!',
        )

    def test_translation_of_images(self) -> None:
        """Tests translation of images"""

        source_directory_path = pathlib.Path(__file__).resolve().parent
        output_directory_path = self.create_test_function_output_directory()
        data_directory_path = source_directory_path / ".." / "Data"
        parameter_directory_path = source_directory_path / "TransformParameters"

        completed = subprocess.run(
            [
                str(self.transformix_exe_file_path),
                "-in",
                str(data_directory_path / "2D_2x2_square_object_at_(2,1).mhd"),
                "-tp",
                str(parameter_directory_path / "Translation(1,-2).txt"),
                "-out",
                str(output_directory_path),
            ],
            capture_output=True,
            check=True,
        )
        self.assertEqual(completed.returncode, 0)

        expected_image = sitk.ReadImage(
            str(data_directory_path / "2D_2x2_square_object_at_(1,3).mhd")
        )
        actual_image = sitk.ReadImage(str(output_directory_path / "result.mhd"))

        self.assert_equal_image_info(actual_image, expected_image)

        actual_pixel_data = sitk.GetArrayFromImage(expected_image)
        expected_pixel_data = sitk.GetArrayFromImage(actual_image)

        max_absolute_difference = 3.0878078e-16
        np.testing.assert_allclose(
            actual_pixel_data, expected_pixel_data, atol=max_absolute_difference, rtol=0
        )

    def test_translation_of_points(self) -> None:
        """Tests translation of points"""

        source_directory_path = pathlib.Path(__file__).resolve().parent
        test_function_output_directory_path = (
            self.create_test_function_output_directory()
        )
        out_directory_path = test_function_output_directory_path / "out"
        out_directory_path.mkdir(exist_ok=True)

        data_directory_path = source_directory_path / ".." / "Data"
        parameter_directory_path = source_directory_path / "TransformParameters"

        completed = subprocess.run(
            [
                str(self.transformix_exe_file_path),
                "-def",
                str(data_directory_path / "2D_unit_square_corner_points.txt"),
                "-tp",
                str(parameter_directory_path / "Translation(1,-2).txt"),
                "-out",
                str(out_directory_path),
            ],
            capture_output=True,
            check=True,
        )
        self.assertEqual(completed.returncode, 0)

        outputpoints_filename = "outputpoints.txt"
        self.assertTrue(
            filecmp.cmp(
                out_directory_path / outputpoints_filename,
                source_directory_path / "ExpectedOutput" / outputpoints_filename,
                shallow=False,
            )
        )

    def test_translation_of_images_and_points(self) -> None:
        """Tests translation of images and points together"""

        source_directory_path = pathlib.Path(__file__).resolve().parent
        output_directory_path = self.create_test_function_output_directory()
        data_directory_path = source_directory_path / ".." / "Data"
        parameter_directory_path = source_directory_path / "TransformParameters"

        completed = subprocess.run(
            [
                str(self.transformix_exe_file_path),
                "-in",
                str(data_directory_path / "2D_2x2_square_object_at_(2,1).mhd"),
                "-def",
                str(data_directory_path / "2D_unit_square_corner_points.txt"),
                "-tp",
                str(parameter_directory_path / "Translation(1,-2).txt"),
                "-out",
                str(output_directory_path),
            ],
            capture_output=True,
            check=True,
        )

        expected_image = sitk.ReadImage(
            str(data_directory_path / "2D_2x2_square_object_at_(1,3).mhd")
        )
        actual_image = sitk.ReadImage(str(output_directory_path / "result.mhd"))

        self.assert_equal_image_info(actual_image, expected_image)

        actual_pixel_data = sitk.GetArrayFromImage(expected_image)
        expected_pixel_data = sitk.GetArrayFromImage(actual_image)

        max_absolute_difference = 3.0878078e-16
        np.testing.assert_allclose(
            actual_pixel_data, expected_pixel_data, atol=max_absolute_difference, rtol=0
        )

        outputpoints_filename = "outputpoints.txt"
        self.assertTrue(
            filecmp.cmp(
                output_directory_path / outputpoints_filename,
                source_directory_path
                / "ExpectedOutput"
                / self.get_name_of_current_function()
                / outputpoints_filename,
                shallow=False,
            )
        )


if __name__ == "__main__":
    # Specify argv to avoid sys.argv to be used directly by unittest.main
    # Note: Use '--verbose' option just as long as the output fits the screen!
    unittest.main(argv=["TransformixTest", "--verbose"])
