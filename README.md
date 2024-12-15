# Overview
This is an application that scrapes websites, 
like Hackernews and Google Research, for tech documents.
It then creates a search engine with a neural network visualizer. 
This tool is simply for me to organize and see what interesting whitepapers come up when I want to learn about a new topic.

Below is a screenshot of my personal knowledge graph. Note: there is more than 100k+ documents so it might take some time to startup the app.
![image](https://github.com/user-attachments/assets/770f488b-a56d-44e6-8957-c9308a10f3f5)

# Installation guide
## Initialization
- Clone the repo
```
git clone --recursive https://github.com/nathang15/rext-stack.git
```
## Backend
- I use python for the entire backend from scraping documents to neural search pipeline implementation.
- Setup the venv and install the requirements
## Frontend
- I use React and no css framework.
```
cd frontend
npm install
```
# Running the app
- just run the main.py file

# Some notice
- At the moment, the application just supports Google Research but I will look into scraping from more blogs site like substack, or medium. But I just use a scraper framework like BeautifulSoup so you can implement this too if you want.
- I will improve the project more in the future but this is just for personal use so feel free to clone this and modify it.

# License
Copyright 2024 Nathan Nguyen
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
