#ifndef _SloanModel_
#define _SloanModel_

#include <vector>
#include "MyModel.h"

class SloanModel : public MyModel
{
	protected:
		int width, height;
		// PSF
		int psf_size, psf_resampling;
		std::vector<double> psfs;
		double bias, gain;

		void add_source_flux(int ibin, int ipsf, double lc, double bc, double M);
		double pixelLogLikelihood(double data, double lambda) const;
	public:
		SloanModel();
};

#endif

