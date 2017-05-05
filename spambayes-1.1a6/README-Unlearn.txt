README FOR ACTIVE UNLEARN 
---------------------------
Important Test Files:
	cluster_feature_test:
	This writes either the pollution rates of the clusters (growing in size) or displays the 
	most significant features of the clusters.
	
	To change the options, the sets list refers to the indices of the data sets to use (referring 	
	to the data sets used for testing (see data_sets.py and the set_dirs method)). 10 refers to 
	Mislabeled-Big, 11 and above are the other mislbaeled data sets. 9 and below refer to the dictionary sets.

	data_set_impact_test:
	Same as above, but does not check for cluster features, and merely returns the unlearned stats.
		
		unlearn_stats:
			au: ActiveUnlearner
			outfile: output file
			data_set: name of the directory
			train: number of unpolluted training ham and spam (as a list)
			test: number of testing ham and spam (as a list)
			polluted: number of testing ham and spam (as a list)
			total_polluted: total number of polluted emails
			total_unpolluted: total number of unpolluted emails
			train_time: total time needed for training
			clusters: whether or not method should return the unlearned clusters
			vanilla: [vanilla original detection rate, vanilla ActiveUnlearner]
			noisy_clusters: whether or not to also check for noisy clusters
			
			
			

ActiveUnlearner:
	Options:
		threshold: detection rate to stop at once reached
		increment: initial increment for clustering
		distance_opt: distance method used (refers to the Distance.py module)
		all_opt: toggles whether or not all of the features are used in determining 				
	  		 distance
		update_opt: determines whether or not the features are updated only when 				         
		            checking clusters or every time features are needed
		greedy_opt: whether or not to use the greedy option in unlearning clusters

Using an ActiveUnlearner:
	Must be initialized with 4 things: a list of the directories containing the training ham, a list of the
	directories containing the training spam, the directory containing the testing ham, and the directory containing
	testing spam. For the two lists, each must contain two directories: the first in each list are the unpolluted
	emails, and the second directory in each list are the polluted emails.

	Any additional arguments may also be provided to override the default arguments. 

Distance Options (Distance.py):
	opt:
		inv-match: finds the number of common features and takes the inverse
		sub-match: find the number of common features and subtract from the
			   number of features in the email that has the greater number
		sub-match-norm: same as above, but divides by the number of features to normalize it to [0, 1]
		None: simply iterates through the features in increasing order and uses edit distance, then comparing 
		      extra features to the empty string
		ac: uses all features that were ever the most significant features for a particular email, and uses the same
		    method as None
		ac-trunc: same as ac, but doesn't do anything with extra features
		trunc: same as None, but doesn't do anything with extra features
		extreme: same as None, but instead compares from the ends of the feature lists going towards the center
		extreme-trunc: same as extreme, but doesn't do anything with extra features
		ac-extreme: same as extreme, but uses all features that wer ever the most significant for a particular email

	is_eu: 
		Toggles whether or not Euclidean-like distance is used (square root of sum of squares; only used for distance
		methods using edit distance).
		
	
		