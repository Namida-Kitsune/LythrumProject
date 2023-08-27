import os
import time
import datetime
import subprocess
import concurrent.futures
import tkinter
import CTkMessagebox #pip install CTkMessagebox
import customtkinter #pip install customtkinter
import tkinter.filedialog
import threading

options = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mpg',
           '.mp3', '.wav', '.aac', '.ogg', '.wma', '.flac', '.m4a']
extension_options = set(options)

class Process:
    def __init__ (self, file_name, file_extension, input_file, output_file, information_file):
        self.file_name = file_name
        self.file_extension = file_extension
        self.input_file = input_file.replace("\\","/")
        self.output_file = output_file.replace("\\","/")
        self.information_file = information_file

def log_error(input_folder, output_folder, file):
    log_file = os.path.join(output_folder,"log_error.txt")
    if not os.path.exists(log_file):
        with open(log_file, 'x', encoding='utf-8') as f:
            pass
    with open(log_file, 'a', encoding='utf-8') as f:
        if os.path.isfile(os.path.join(input_folder, file)):
            f.write(f'The {file} file is not converted. Date: ')
        else:
            f.write(f'{file} is folder. Date: ')
        f.write(f'{datetime.datetime.now().strftime("%d %B %Y %H:%M:%S")}\n')

def create_process(input_folder, output_folder, input_extension, output_extension):
    extension = {input_extension}
    if input_extension == 'ALL':
        extension = extension_options
    process = []
    for file in os.listdir(input_folder):
        result = os.path.splitext(file)
        file_name, file_extension = result[0], result[1].lower()
        if(file_extension in extension):
            input_file = os.path.join(input_folder,file)
            output_file = os.path.join(output_folder,file_name+output_extension)
            information_file = os.stat(input_file)
            process.append(Process(file_name, file_extension, input_file, output_file, information_file))
        else:
            log_error(input_folder, output_folder, file)
    return process

def shortest_job_first(process):
    return sorted(process, key = lambda process : process.information_file.st_size)

def auto_select_gpu(ffmpeg, input_file, output_file, video_codec='libx264', audio_codec='libmp3lame', gpu=0):
    output_extension = os.path.splitext(output_file)[1].lower()
    if os.path.isfile(output_file):
        os.remove(output_file)
    if output_extension in {'.mp3', '.wav', '.aac', '.ogg', '.wma', '.flac', '.m4a'}:
        if output_extension == '.wav':
            audio_codec = 'pcm_s16le'
        elif output_extension == '.aac':
            audio_codec = 'aac'
        elif output_extension == '.ogg':
            audio_codec = 'libvorbis'
        elif output_extension == '.wma':
            audio_codec = 'wmav2'
        elif output_extension == '.flac':
            audio_codec = 'flac'
        elif output_extension == '.m4a':
            audio_codec = 'aac -strict experimental'
        ffmpeg_cmd = f'{ffmpeg} -i "{input_file}" -vn -acodec {audio_codec} "{output_file}"'
        gpu=3
    else:
        if output_extension in {'.mp4', '.avi', '.mkv', '.webm', '.mpg'}:
            video_codec_gpu = ''
            if gpu < 3:
                if output_extension == '.webm':
                    video_codec = 'av1'
                elif output_extension == '.mpg':
                    video_codec = 'mpeg2'
                    video_codec_gpu = '_qsv'
                    gpu=3
                else:
                    video_codec = 'h264'
                
            if gpu == 0:
                video_codec_gpu = '_nvenc'
            elif gpu == 1:
                video_codec_gpu = '_amf'
            elif gpu == 2:
                video_codec_gpu = '_qsv'
                
            ffmpeg_cmd = f'{ffmpeg} -i "{input_file}" -vcodec {video_codec}{video_codec_gpu} -acodec {audio_codec} "{output_file}"'
        else:
            if output_extension == '.mov':
                audio_codec='aac'
            ffmpeg_cmd = f'{ffmpeg} -i "{input_file}" -vcodec {video_codec} -acodec {audio_codec} "{output_file}"'
            gpu=3
    if gpu > 2:
        try:
            subprocess.run(ffmpeg_cmd, shell=True, check=True)
        except:
            if os.path.isfile(output_file):
                os.remove(output_file)
            log_error(os.path.dirname(input_file), os.path.dirname(output_file), os.path.basename(input_file))
    else:
        try:
            subprocess.run(ffmpeg_cmd, shell=True, check=True)
        except:
            return auto_select_gpu(ffmpeg, input_file, output_file, gpu=gpu+1)

def convert_file(process):
    input_file = process.input_file
    output_file = process.output_file
    ffmpeg = os.path.join(os.getcwd(), 'assets', 'ffmpeg', 'bin', 'ffmpeg.exe')
    auto_select_gpu(ffmpeg, input_file, output_file)

def convert():
    if input_path.get():
        input_folder = input_path.get()
        if output_path.get():
            input_extension = combobox_input_select.get()
            output_extension = combobox_output_select.get()
            output_folder = os.path.join(output_path.get(), f'OUTPUT_{output_extension.replace(".", "").upper()}')
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            process = shortest_job_first(create_process(input_folder, output_folder, input_extension, output_extension))
            process_amount = len(process)
            time.sleep(0.5)
            start_time = time.time()
            if process_amount > 0:
                process_step = (((1 / process_amount) * 100) / 100) * 50
                btn_convert.configure(state='disabled', text='Converting...')
                progressbar.configure(determinate_speed=process_step)
                progressbar.set(0)
                workers = process_amount if process_amount < 5 else 4
                progressbar.grid(row=5, column=1, columnspan=2, padx=10, pady=10, sticky='nsew')
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = [executor.submit(convert_file, p) for p in process]
                    for futures in concurrent.futures.as_completed(futures):
                        progressbar.step()
                progressbar.grid_forget()
            btn_convert.configure(state='normal', text='Convert')
            CTkMessagebox.CTkMessagebox(title="Success",icon='check' , message=f'Complete file conversion in {(time.time()-start_time):.2f} seconds', sound='enable')
        else:
            time.sleep(0.5)
            CTkMessagebox.CTkMessagebox(title="Warning",icon='warning' , message='Please select folder output.', sound='enable')
            btn_convert.configure(state='normal', text='Convert')
    else:
        time.sleep(0.)
        CTkMessagebox.CTkMessagebox(title="Warning",icon='warning' , message='Please select folder input.', sound='enable')
        btn_convert.configure(state='normal', text='Convert')

def start_convert_thread():
    btn_convert.configure(state='disabled', text='Checking...')
    convert_thread = threading.Thread(target=convert)
    convert_thread.start()

def browse_folder_input():
    folder_path = tkinter.filedialog.askdirectory()
    if folder_path:
        input_path.set(folder_path)

def browse_folder_output():
    folder_path = tkinter.filedialog.askdirectory()
    if folder_path:
        output_path.set(folder_path)

if __name__ == '__main__':
    customtkinter.set_appearance_mode('System')
    color_theme = os.path.join(os.getcwd(),'assets','custom_theme.json')
    icon_theme = os.path.join(os.getcwd(),'assets','icon.ico')
    if not os.path.exists(color_theme):
        color_theme = 'dark-blue'
    customtkinter.set_default_color_theme(color_theme)
    root = customtkinter.CTk()
    root.title('Lythrum')
    root.iconbitmap(icon_theme)
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=2)
    root.columnconfigure(2, weight=2)
    root.columnconfigure(3, weight=1)
    root.rowconfigure(0, weight=1)
    root.rowconfigure(1, weight=1)
    root.rowconfigure(2, weight=1)
    root.rowconfigure(3, weight=1)
    
    lbl_input = customtkinter.CTkLabel(root, text='INPUT')
    lbl_input.grid(row=0, column=1, columnspan=2, padx=10, pady=10, sticky='nsew')
    
    lbl_output = customtkinter.CTkLabel(root, text='OUTPUT')
    lbl_output.grid(row=2, column=1, columnspan=2, padx=10, pady=10, sticky='nsew')

    btn_input = customtkinter.CTkButton(root, text='Select Folder Input', command=browse_folder_input)
    btn_input.grid(row=1, column=0, padx=10, pady=10, sticky='ew')

    btn_output = customtkinter.CTkButton(root, text='Select Folder Output', command=browse_folder_output)
    btn_output.grid(row=3, column=0, padx=10, pady=10, sticky='ew')

    input_path = tkinter.StringVar()
    entry_input = customtkinter.CTkEntry(root, textvariable=input_path, state='readonly')
    entry_input.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky='ew')

    output_path = tkinter.StringVar()
    entry_output = customtkinter.CTkEntry(root, textvariable=output_path, state='readonly')
    entry_output.grid(row=3, column=1, columnspan=2, padx=10, pady=10, sticky='ew')
    
    combobox_input_options = options.copy()
    combobox_input_options.insert(0, 'ALL')
    combobox_input_select = tkinter.StringVar(value=combobox_input_options[0])
    combobox_input = customtkinter.CTkOptionMenu(root, values=combobox_input_options, variable=combobox_input_select, dynamic_resizing='enable')
    combobox_input.grid(row=1, column=3, padx=10, pady=10, sticky='ew')

    combobox_output_options = options
    combobox_output_select = tkinter.StringVar(value=combobox_output_options[0])
    combobox_output = customtkinter.CTkOptionMenu(root, values=combobox_output_options, variable=combobox_output_select, dynamic_resizing='enable')
    combobox_output.grid(row=3, column=3, padx=10, pady=10, sticky='ew')

    btn_convert = customtkinter.CTkButton(root, text='Convert', command=start_convert_thread)
    btn_convert.grid(row=4, column=1, columnspan=2, padx=10, pady=10, sticky='nsew')

    progressbar = customtkinter.CTkProgressBar(root, mode='determinate', orientation='horizontal')
    progressbar.set(0)
    progressbar.grid_forget()
    root.mainloop()
