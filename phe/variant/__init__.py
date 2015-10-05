"""Classes and methods to work with variants and such."""
import abc
import pickle

from vcf import filters
import vcf
from vcf.parser import _Filter

from phe.variant_filters import make_filters, PHEFilterBase


class VCFTemplate(object):
    """This is a small hack class for the Template used in generating
    VCF file."""

    def __init__(self, vcf_reader):
        self.infos = vcf_reader.infos
        self.formats = vcf_reader.formats
        self.filters = vcf_reader.filters
        self.alts = vcf_reader.alts
        self.contigs = vcf_reader.contigs
        self.metadata = vcf_reader.metadata
        self._column_headers = vcf_reader._column_headers
        self.samples = vcf_reader.samples

class VariantSet(object):
    """A convenient representation of set of variants.
    TODO: Implement iterator and generator for the variant set.
    """

    def __init__(self, vcf_in, filters=None):
        """Constructor of variant set.
        
        Parameters:
        -----------
        vcf_in: str
            Path to the VCF file for loading information.
        filters: dict, optional
            Dictionary of the filter, threshold key value pairs.
        """
        self.vcf_in = vcf_in

        self.out_template = None

        self.filters = []
        if filters is not None:
            self.filters = make_filters(config=filters)
        else:
            reader = vcf.Reader(filename=self.vcf_in)
            filters = {}
            for filter_id in reader.filters:
                filters.update(PHEFilterBase.decode(filter_id))

            if filters:
                self.filters = make_filters(config=filters)

        self.variants = []

    def filter_variants(self, keep_only_snps=True):
        """Create a variant """

        # Create a reader class from input VCF.
        reader = vcf.Reader(filename=self.vcf_in)

        # Add each filter we are going to use to the record.
        # This is needed for writing out proper #FILTER header in VCF.
        for record_filter in self.filters:
            # We know that each filter has short description method.
            short_doc = record_filter.short_desc()
            short_doc = short_doc.split('\n')[0].lstrip()

            reader.filters[record_filter.filter_name()] = _Filter(record_filter.filter_name(), short_doc)

        # For each record (POSITION) apply set of filters.
        for record in reader:
            for record_filter in self.filters:

                # Call to __call__ method in each filter.
                result = record_filter(record)

                # Record is KEPT if filter returns None
                if result == None:
                    continue

                # If we got this far, then record is filtered OUT.
                record.add_filter(record_filter.filter_name())

            # After applying all filters, check if FILTER is None.
            # If it is, then record PASSED all filters.
            if record.FILTER is None:
                record.FILTER = 'PASS'
                # FIXME: Does this work for indels?
                if keep_only_snps and record.is_snp:
                    self.variants.append(record)
            else:
                self.variants.append(record)

        self.out_template = VCFTemplate(reader)

        return [ variant for variant in self.variants if variant.FILTER == "PASS"]


    def write_variants(self, vcf_out, only_snps=False, only_good=False):
        """Write variants to a VCF file.
        
        Parameters:
        -----------
        vcf_out: str
            Path to the file where VCF data is written.
        only_snps: bool, optional
            True is *only* SNP are to be written to the output (default: False).
        only_good: bool, optional
            True if only those records that PASS all filters should be written
            (default: False).
        
        Returns:
        int:
            Number of records written.
        """
        written_variants = 0
        with open(vcf_out, "w") as out_vcf:
            writer = vcf.Writer(out_vcf, self.out_template)
            for record in self.variants:

                if only_snps and not record.is_snp:
                    continue

                if only_good and record.FILTER != "PASS" or record.FILTER is None:
                    continue

                writer.write_record(record)
                written_variants += 1

        return written_variants

    def _write_bad_variants(self, vcf_out):
        """**PRIVATE:** Write only those records that **haven't** passed."""
        written_variants = 0
        with open(vcf_out, "w") as out_vcf:
            writer = vcf.Writer(out_vcf, self.out_template)
            for record in self.variants:
                if record.FILTER != "PASS" and record.FILTER is not None:
                    writer.write_record(record)
                    written_variants += 1
        return written_variants

    def serialise(self, out_file):
        """Save the data in this class to a file for future use/reload.
        
        Parameters:
        -----------
        out_file: str
            path to file where the data should be written to.
            
        Returns:
        --------
        int:
            Number of variants written.
        """
        written_variants = 0
        with open(out_file, "w") as out_vcf:
            writer = vcf.Writer(out_vcf, self.out_template)
            for record in self.variants:
                writer.write_record(record)
                written_variants += 1

        return written_variants


class VariantCaller(object):
    """Abstract class used for access to the implemented variant callers."""

    __metaclass__ = abc.ABCMeta

    def __init__(self, cmd_options=None):
        """Constructor for variant caller.
        
        Parameters:
        -----------
        cmd_options: str, optional
            Command options to pass to the variant command.
        """
        self.cmd_options = cmd_options

    @abc.abstractmethod
    def make_vcf(self, *args, **kwargs):
        """Create a VCF from **BAM** file.
        
        Parameters:
        -----------
        ref: str
            Path to the reference file.
        bam: str
            Path to the indexed **BAM** file for calling variants.
        vcf_file: str
            path to the VCF file where data will be written to.
            
        Returns:
        --------
        bool:
            True if variant calling was successful, False otherwise.
        """
        raise NotImplementedError("make_vcf is not implemented yet.")

    @abc.abstractmethod
    def create_aux_files(self, ref):
        """Create needed (if any) auxiliary files.
        These files are required for proper functioning of the variant caller.
        """
        raise NotImplementedError("create_aux_files is not implemeted.")
