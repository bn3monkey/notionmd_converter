from selenium import webdriver
import os

c = webdriver.Chrome()

html_file = "file:///" + os.getcwd() + "//test//html//Jei2_Project.html"

c.get(html_file)

from pdfy import Pdfy

p = Pdfy()

p.html_to_pdf(html_file, "test.pdf")
