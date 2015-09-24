'''
Created on 24 Sep 2015

@author: alex
'''

import argparse
import logging

from phe.variant_filters import PHEFilterBase


class ADFilter(PHEFilterBase):
    '''Filter sites by AD ratio.'''


    name = "ADRatio"
    _default_threshold = 0.9
    _parameter = "ad_ratio"

    @classmethod
    def customize_parser(self, parser):
        arg_name = self._parameter.replace("_", "-")
        parser.add_argument("--%s" % arg_name, type=float, default=self._default_threshold,
                help="Filter sites below minimum ad ratio (default: %s)" % self._default_threshold)

    def __init__(self, args):
        """Min Depth constructor."""
        # This needs to happen first, because threshold is initialised here.
        super(ADFilter, self).__init__(args)

        # Change the threshold to custom dp value.
        self.threshold = self._default_threshold
        if isinstance(args, argparse.Namespace):
            self.threshold = args.ad_ratio
        elif isinstance(args, dict):
            self.threshold = args.get(self._parameter)

    def __call__(self, record):
        """Filter a :py:class:`vcf.model._Record`."""

        if len(record.samples) > 1:
            logging.warn("More than 1 sample detected. Only first is considered.")

        record_ad = record.samples[0].data.AD
        try:

            # FIXME: when record length is > 2, what do you do?
            assert len(record_ad) == 2, "AD data is incomplete POS: %i" % record.POS

            ratio = float(record_ad[1]) / (record_ad[1] + record_ad[0])
        except Exception:
            logging.error("Could not calculate AD ratio from %s POS: %s", record_ad, record.POS)
            ratio = None

        if ratio is None or ratio < self.threshold:
            # FIXME: When ratio is None, i.e. error, what do you do?
            return ratio or ""
        else:
            return None

    def short_desc(self):
        short_desc = self.__doc__ or ''

        if short_desc:
            short_desc = "%s (AD ratio > %s)" % (short_desc, self.threshold)

        return short_desc