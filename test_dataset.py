from torchvision import datasets

dataset = datasets.ImageFolder("dataset")

print(dataset.classes)
print(len(dataset))