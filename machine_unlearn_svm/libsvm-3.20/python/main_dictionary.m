% Proprocesses emails in dataset
sets = {'Set1', 'Set2', 'Set3'};

polluted_percentage = .5;
directory = 'DictionarySets-1.1';
o_directory = [directory '-processed'];
mkdir(o_directory);

fprintf(['Preprocessing emails from ' directory '\n']);

hams = {};
spams = {};

for i = 1:size(sets,2)
    hams{i} = ['Ham/' sets{i}];
    spams{i} = ['Spam/' sets{i}];
end

fprintf('Processing Hams\n');
mkdir(o_directory, 'Ham'); % make mislabeled/Ham

for i = 1:size(sets,2)
    % make mislabeled/Ham/Set1
    dir_name = hams{i};
    mkdir([o_directory '/' dir_name]);
    dir_list = readdir([directory '/' dir_name]);
    dir_list([1,2],:) = []; % remove . and .. files
    output = [o_directory '/' dir_name '/data'];
    fid = fopen(output, 'w+');
    fputs(fid, "\n");
    fclose(fid);
    if i == 2
        dir_size = 3000;
    elseif i == 1
        dir_size = size(dir_list,1) * (1-polluted_percentage); % number of unpolluted
    else
        dir_size = size(dir_list,1);
    endif
    fid = fopen(output, 'w+');
    for j = 1:dir_size
        fprintf([dir_name ': ' num2str(j) '/' num2str(dir_size) '\n']);
        f_ = dir_list{j};
        filename = [directory '/' dir_name '/' f_];
        file_contents = readFile(filename);
        word_indices  = processEmail(file_contents);
        x             = emailFeatures(word_indices);
        fputs(fid, '-1 ');
        for k = 1:size(x,1)
            fputs(fid, [num2str(k) ':' num2str(x(k,1)) ' ']);
        end
        fputs(fid, "\n");
        
    end
    fclose(fid);
end
