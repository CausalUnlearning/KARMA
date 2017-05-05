% Proprocesses emails in dataset
sets = {'Set1', 'Set2', 'Set3'};

polluted_percentage = .5;
directory = 'DictionarySets-1.1';
o_directory = [directory '-processed'];

fprintf(['Preprocessing emails from ' directory '\n']);

hams = {};
spams = {};

for i = 1:size(sets,2)
    hams{i} = ['Ham/' sets{i}];
    spams{i} = ['Spam/' sets{i}];
end

fprintf('Processing Spams\n');
mkdir(o_directory, 'Spam'); % make mislabeled/Spam

for i = 1:size(sets,2)
    % make mislabeled/Spam/Set
    dir_name = spams{i};
    mkdir([o_directory '/' dir_name]);
    dir_list = readdir([directory '/' dir_name]);
    dir_list([1,2],:) = []; % remove . and .. files
    output = [o_directory '/' dir_name '/data'];
    if i == 2
        dir_size = 3000;
    elseif i == 1
        dir_size = size(dir_list,1) * (1-polluted_percentage); % number of unpolluted
    else
        dir_size = 12000 * polluted_percentage; % number of polluted 
    endif
    if i == 3 % processing the spams
        s = 0
        step_size = floor(26000 / dir_size)
        fid = fopen(output, 'w+');
        for j = 1:dir_size
            s = s + step_size % get every step_size-th dictionary email
            fprintf([dir_name ': ' num2str(j) '/' num2str(dir_size) '\n']);
            f_ = dir_list{s};
            filename = [directory '/' dir_name '/' f_];
            file_contents = readFile(filename);
            word_indices  = processEmail(file_contents);
            x             = emailFeatures(word_indices);
            fputs(fid, '+1 ');
            for k = 1:size(x,1)
                fputs(fid, [num2str(k) ':' num2str(x(k,1)) ' ']);
            end
            fputs(fid, "\n");
        end
        fclose(fid);
    else
        fid = fopen(output, 'w+');
        for j = 1:dir_size
            fprintf([dir_name ': ' num2str(j) '/' num2str(dir_size) '\n']);
            f_ = dir_list{j};
            filename = [directory '/' dir_name '/' f_];
            file_contents = readFile(filename);
            word_indices  = processEmail(file_contents);
            x             = emailFeatures(word_indices);
            fputs(fid, '+1 ');
            for k = 1:size(x,1)
                fputs(fid, [num2str(k) ':' num2str(x(k,1)) ' ']);
            end
            fputs(fid, "\n"); 
        end
        fclose(fid);
    endif
end
